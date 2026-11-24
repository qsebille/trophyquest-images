from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass

from image_uploader.postgres.connection import Connection, get_postgres_connection


@dataclass(frozen=True)
class ImageSource:
    kind: str
    table: str
    id_type: str
    source_column: str
    destination_column: str
    igdb_game_column: str | None = None

    @property
    def eligibility(self) -> str:
        if self.igdb_game_column is None:
            return "TRUE"
        return f"""
            EXISTS (
                SELECT 1
                FROM app.igdb_matching AS matching
                WHERE matching.matched_game_id = image.{self.igdb_game_column}
                  AND matching.status IN ('AUTO_MATCH', 'MANUAL_MATCH')
            )
        """


PSN_AVATAR = ImageSource("psn-player", "psn.player", "uuid", "psn_avatar_url", "aws_avatar_url")
PSN_SUITE = ImageSource("psn-suite", "psn.suite", "uuid", "psn_image_url", "aws_image_url")
PSN_TROPHY = ImageSource("psn-trophy", "psn.trophy", "uuid", "psn_icon_url", "aws_icon_url")
IGDB_COVER = ImageSource("igdb-cover", "igdb.game", "bigint", "igdb_cover_url", "aws_cover_url", "id")
IGDB_BACKGROUND = ImageSource(
    "igdb-background", "igdb.game", "bigint", "igdb_background_url", "aws_background_url", "id"
)
IGDB_SCREENSHOT = ImageSource("igdb-screenshot", "igdb.screenshot", "text", "igdb_url", "aws_url", "game_id")
IGDB_SOURCES = (IGDB_COVER, IGDB_BACKGROUND, IGDB_SCREENSHOT)
SOURCES_BY_KIND = {
    source.kind: source for source in (PSN_AVATAR, PSN_SUITE, PSN_TROPHY, *IGDB_SOURCES)
}


def fetch_pending_images(
    connection: Connection, sources: tuple[ImageSource, ...], limit: int
) -> Sequence[Sequence[str]]:
    if limit == 0:
        return []

    # The table and column identifiers come from the source definitions above.
    selects = [
        f"""
            SELECT image.id::text AS id, image.{source.source_column} AS url, %s::text AS kind, image.created_at
            FROM {source.table} AS image
            WHERE image.{source.destination_column} IS NULL
              AND image.{source.source_column} ~ '[^[:space:]]'
              AND {source.eligibility}
        """
        for source in sources
    ]
    pending = " UNION ALL ".join(selects)
    query = f"""
        SELECT id, url, kind
        FROM ({pending}) AS pending
        ORDER BY created_at, kind, id
        LIMIT %s
    """
    parameters = tuple(source.kind for source in sources) + (limit,)
    with closing(connection.cursor()) as cursor:
        cursor.execute(query, parameters)
        return cursor.fetchall()


def save_uploaded_url(source: ImageSource, image_id: str, original_url: str, public_url: str) -> bool:
    query = f"""
        UPDATE {source.table} AS image
        SET {source.destination_column} = %s
        WHERE image.id = CAST(%s AS {source.id_type})
          AND image.{source.source_column} = %s
          AND image.{source.destination_column} IS NULL
          AND {source.eligibility}
    """
    with closing(get_postgres_connection()) as connection, closing(connection.cursor()) as cursor:
        cursor.execute(query, (public_url, image_id, original_url))
        saved = cursor.rowcount == 1
        connection.commit()
        return saved
