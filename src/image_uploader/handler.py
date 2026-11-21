import logging

from image_uploader.run import run_image_uploader

DEFAULT_LIMIT = 20


def _read_limit(event: dict, name: str) -> int:
    value = event.get(name, DEFAULT_LIMIT)
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        value = int(value)
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def image_uploader_handler(event, context):
    logging.getLogger().setLevel(logging.INFO)
    if event is None:
        event = {}
    if not isinstance(event, dict):
        raise ValueError("The Lambda event must be an object")

    run_image_uploader(
        player_avatar_limit=_read_limit(event, "player_avatar_limit"),
        trophy_icon_limit=_read_limit(event, "trophy_icon_limit"),
        trophy_suite_image_limit=_read_limit(event, "trophy_suite_image_limit"),
        igdb_image_limit=_read_limit(event, "igdb_image_limit"),
    )
