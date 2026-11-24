import json
from unittest.mock import Mock

from image_uploader.postgres import connection


def test_postgres_secret_is_reused_and_refreshed(monkeypatch):
    secret_arn = "arn:aws:secretsmanager:eu-west-3:123456789012:secret:test"
    settings = {
        "host": "db.example",
        "port": "5432",
        "dbname": "trophyquest",
        "username": "image_uploader",
        "password": "test-password",
    }
    client = Mock()
    get_secret_value = client.return_value.get_secret_value
    get_secret_value.side_effect = [
        {"SecretString": json.dumps(settings)},
        {"SecretString": json.dumps(settings | {"password": "rotated-password"})},
    ]
    connect = Mock()
    monkeypatch.setenv("POSTGRES_SECRET_ARN", secret_arn)
    monkeypatch.setattr(connection.boto3, "client", client)
    monkeypatch.setattr(connection, "connect", connect)
    monkeypatch.setattr(connection, "monotonic", Mock(side_effect=[10, 20, 310]))

    connection.get_postgres_connection()
    connection.get_postgres_connection()
    connection.get_postgres_connection()

    client.assert_called_with("secretsmanager")
    get_secret_value.assert_called_with(SecretId=secret_arn)
    assert get_secret_value.call_count == 2
    assert client.return_value.close.call_count == 2
    assert [call.kwargs["password"] for call in connect.call_args_list] == [
        "test-password", "test-password", "rotated-password",
    ]
    connect.assert_called_with(
        host="db.example",
        port=5432,
        database="trophyquest",
        user="image_uploader",
        password="rotated-password",
        timeout=10,
    )
