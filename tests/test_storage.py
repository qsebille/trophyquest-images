from unittest.mock import MagicMock, Mock

import pytest
from requests import HTTPError

from image_uploader import handler, run
from image_uploader.utils import aws


def test_handler_uses_defaults_and_accepts_zero_limits(monkeypatch):
    run_uploader = Mock()
    monkeypatch.setattr(handler, "run_image_uploader", run_uploader)

    handler.image_uploader_handler({"igdb_image_limit": "0", "game_image_limit": 10}, None)

    run_uploader.assert_called_once_with(
        player_avatar_limit=20,
        trophy_icon_limit=20,
        trophy_suite_image_limit=20,
        igdb_image_limit=0,
    )


@pytest.mark.parametrize("value", [-1, True, 1.5, "invalid"])
def test_handler_rejects_invalid_limits(monkeypatch, value):
    run_uploader = Mock()
    monkeypatch.setattr(handler, "run_image_uploader", run_uploader)

    with pytest.raises(ValueError, match="igdb_image_limit"):
        handler.image_uploader_handler({"igdb_image_limit": value}, None)

    run_uploader.assert_not_called()


def test_upload_sets_the_content_type_and_returns_a_browser_url(monkeypatch):
    response = MagicMock()
    response.headers = {"Content-Type": "image/png; charset=binary"}
    response.iter_content.return_value = [b"image", b" bytes"]
    get = MagicMock()
    get.return_value.__enter__.return_value = response
    monkeypatch.setattr(aws.requests, "get", get)
    uploaded = {}

    def put_object(**kwargs):
        uploaded.update(kwargs | {"Body": kwargs["Body"].read()})

    s3 = Mock(put_object=put_object)
    url = aws.upload_image_to_aws(
        "https://source.example/avatar?query=value", "psn-player/test id", s3, "bucket", "https://images.example"
    )

    assert uploaded == {
        "Bucket": "bucket",
        "Key": "psn-player/test id.png",
        "Body": b"image bytes",
        "ContentType": "image/png",
    }
    assert url == "https://images.example/psn-player/test%20id.png"


def test_failed_http_request_does_not_write_to_s3(monkeypatch):
    get = MagicMock()
    get.return_value.__enter__.return_value.raise_for_status.side_effect = HTTPError("Not found")
    monkeypatch.setattr(aws.requests, "get", get)
    s3 = Mock()

    with pytest.raises(HTTPError):
        aws.upload_image_to_aws("https://source.example/missing.png", "test", s3, "bucket", "https://images.example")

    s3.put_object.assert_not_called()


def test_failed_s3_upload_does_not_write_to_postgres(monkeypatch):
    upload = Mock(side_effect=RuntimeError("S3 error"))
    save = Mock()
    monkeypatch.setattr(run, "upload_image_to_aws", upload)
    monkeypatch.setattr(run, "save_uploaded_url", save)

    with pytest.raises(RuntimeError, match="S3 error"):
        run.upload_pending_image(
            ("player-id", "https://source.example/old.png", "psn-player"),
            "bucket",
            Mock(),
            public_base_url="https://images.example",
        )

    save.assert_not_called()


def test_an_avatar_change_uses_a_new_object_key_and_rejects_an_old_update(monkeypatch):
    upload = Mock(return_value="https://images.example/avatar.png")
    save = Mock(side_effect=[False, True])
    monkeypatch.setattr(run, "upload_image_to_aws", upload)
    monkeypatch.setattr(run, "save_uploaded_url", save)
    s3 = Mock()
    old_url = "https://source.example/old.png"
    new_url = "https://source.example/new.png"

    assert run.upload_pending_image(
        ("player-id", old_url, "psn-player"), "bucket", s3, public_base_url="https://images.example"
    ) is None
    assert run.upload_pending_image(
        ("player-id", new_url, "psn-player"), "bucket", s3, public_base_url="https://images.example"
    ) == "https://images.example/avatar.png"

    assert upload.call_args_list[0].args[1] != upload.call_args_list[1].args[1]
    assert [call.args[2] for call in save.call_args_list] == [old_url, new_url]
