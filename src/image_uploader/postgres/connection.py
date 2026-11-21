import os

from pg8000.dbapi import Connection, connect


def get_postgres_connection() -> Connection:
    return connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        database=os.environ["POSTGRES_DATABASE"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        timeout=10,
    )
