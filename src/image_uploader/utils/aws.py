from io import BytesIO
from mimetypes import guess_type
from urllib.parse import quote, urlsplit

import requests


MAX_IMAGE_BYTES = 16 * 1024 * 1024
IMAGE_EXTENSIONS = {
    "image/avif": "avif",
    "image/bmp": "bmp",
    "image/gif": "gif",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/x-icon": "ico",
    "image/vnd.microsoft.icon": "ico",
    "image/x-png": "png",
}
CANONICAL_TYPES = {"image/jpg": "image/jpeg", "image/x-png": "image/png"}


def image_base_url(bucket_name: str, configured_url: str | None) -> str:
    base_url = configured_url if configured_url is not None else f"https://{bucket_name}.s3.amazonaws.com"
    parts = urlsplit(base_url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.query or parts.fragment:
        raise ValueError("IMAGES_PUBLIC_BASE_URL must be an HTTPS base URL")
    return base_url.rstrip("/")


def upload_image_to_aws(
        image_url: str,
        s3_path: str,
        s3_client,
        bucket_name: str,
        public_base_url: str,
) -> str:
    with requests.get(image_url, stream=True, timeout=(5, 15)) as response, BytesIO() as body:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").partition(";")[0].strip().lower()
        if content_type in ("", "application/octet-stream", "binary/octet-stream"):
            content_type = guess_type(urlsplit(response.url).path)[0] or ""
        extension = IMAGE_EXTENSIONS.get(content_type)
        if extension is None:
            raise ValueError("Unsupported image content type")

        for chunk in response.iter_content(chunk_size=64 * 1024):
            if body.tell() + len(chunk) > MAX_IMAGE_BYTES:
                raise ValueError("Image exceeds the maximum download size")
            body.write(chunk)
        if body.tell() == 0:
            raise ValueError("Downloaded image is empty")

        s3_key = f"{s3_path}.{extension}"
        body.seek(0)
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=body,
            ContentType=CANONICAL_TYPES.get(content_type, content_type),
        )

    return f"{public_base_url}/{quote(s3_key, safe='/')}"
