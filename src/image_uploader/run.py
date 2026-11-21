import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from functools import partial
from hashlib import sha256

import boto3
import dotenv
from botocore.config import Config

from image_uploader.postgres.connection import get_postgres_connection
from image_uploader.postgres.images import (
    IGDB_SOURCES,
    PSN_AVATAR,
    PSN_SUITE,
    PSN_TROPHY,
    SOURCES_BY_KIND,
    fetch_pending_images,
    save_uploaded_url,
)
from image_uploader.utils.aws import image_base_url, upload_image_to_aws
from image_uploader.utils.process_image_batch import process_image_batch

logger = logging.getLogger(__name__)


def upload_pending_image(record, bucket_name: str, s3_client, *, public_base_url: str) -> str | None:
    image_id, original_url, kind = record
    source = SOURCES_BY_KIND[kind]
    url_hash = sha256(original_url.encode()).hexdigest()
    key = f"{source.kind}/{image_id}/{url_hash}"
    public_url = upload_image_to_aws(original_url.strip(), key, s3_client, bucket_name, public_base_url)
    if save_uploaded_url(source, image_id, original_url, public_url):
        return public_url

    logger.info("Skipping database update for %s image %s because the row changed", kind, image_id)
    return None


def run_image_uploader(
        player_avatar_limit: int,
        trophy_icon_limit: int,
        trophy_suite_image_limit: int,
        igdb_image_limit: int,
):
    dotenv.load_dotenv()
    bucket_name = os.environ["IMAGES_BUCKET_NAME"]
    public_base_url = image_base_url(bucket_name, os.environ.get("IMAGES_PUBLIC_BASE_URL"))
    max_workers = int(os.environ.get("IMAGES_MAX_WORKERS", "16"))
    if max_workers < 1:
        raise ValueError("IMAGES_MAX_WORKERS must be positive")

    limits = (
        ("player_avatar", (PSN_AVATAR,), player_avatar_limit),
        ("trophy_icon", (PSN_TROPHY,), trophy_icon_limit),
        ("trophy_suite", (PSN_SUITE,), trophy_suite_image_limit),
        ("igdb", IGDB_SOURCES, igdb_image_limit),
    )
    with closing(get_postgres_connection()) as connection:
        batches = [
            (label, fetch_pending_images(connection, sources, limit))
            for label, sources, limit in limits
        ]

    upload = partial(upload_pending_image, public_base_url=public_base_url)
    total_results = []
    s3_config = Config(
        connect_timeout=5,
        read_timeout=15,
        max_pool_connections=max_workers,
        retries={"mode": "standard", "total_max_attempts": 3},
    )
    with closing(boto3.client("s3", config=s3_config)) as s3_client, ThreadPoolExecutor(max_workers=max_workers) as executor:
        for label, images in batches:
            results, errors = process_image_batch(executor, images, upload, bucket_name, s3_client, label)
            total_results.extend(results)
            logger.info("%s: selected=%d saved=%d failed=%d", label, len(images), len(results), len(errors))

    return total_results
