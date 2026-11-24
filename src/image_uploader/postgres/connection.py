import json
import os
from contextlib import closing
from functools import lru_cache
from time import monotonic

import boto3
from pg8000.dbapi import Connection, connect


@lru_cache(maxsize=1)
def _read_postgres_secret(secret_arn: str, refresh_window: int) -> dict:
    with closing(boto3.client("secretsmanager")) as client:
        response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response["SecretString"])


def get_postgres_connection() -> Connection:
    secret_arn = os.getenv("POSTGRES_SECRET_ARN")
    if secret_arn:
        settings = _read_postgres_secret(secret_arn, int(monotonic() // 300))
        return connect(
            host=settings["host"],
            port=int(settings["port"]),
            database=settings["dbname"],
            user=settings["username"],
            password=settings["password"],
            timeout=10,
        )

    return connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        database=os.environ["POSTGRES_DATABASE"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        timeout=10,
    )
