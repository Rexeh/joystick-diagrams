"""The ``device_inventory`` table: when each controller GUID was first and last read.

One row per GUID. ``first_seen``/``last_seen`` are the ISO-8601 UTC stamps of
the reads that produced it, so "new since last read" is ``first_seen`` equal to
the most recent stamp. ``normalised_name`` (``normalise_device_name``) is what
GUID inheritance compares exactly. ``notices_json`` holds the messages the
inventory attached to the row (kept template, possible duplicate) until a screen
clears them. The per-read facts (``last_seen``, ``games_json``) that screens
show also live on the ``devices`` row (``db_device_management``).
"""

from dataclasses import dataclass

from joystick_diagrams.db.db_connection import connection

TABLE_NAME = "device_inventory"

COLUMNS = (
    "guid",
    "name",
    "normalised_name",
    "first_seen",
    "last_seen",
    "read_count",
    "notices_json",
)
_SELECT_COLUMNS = ", ".join(COLUMNS)


@dataclass(frozen=True)
class InventoryRow:
    guid: str
    name: str | None
    normalised_name: str | None
    first_seen: str | None
    last_seen: str | None
    read_count: int
    notices_json: str | None


def _row(record) -> InventoryRow:
    guid, name, normalised, first, last, count, notices = record
    return InventoryRow(guid, name, normalised, first, last, int(count or 0), notices)


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}("
        "guid TEXT PRIMARY KEY, "
        "name TEXT, "
        "normalised_name TEXT, "
        "first_seen TEXT, "
        "last_seen TEXT, "
        "read_count INTEGER NOT NULL DEFAULT 0, "
        "notices_json TEXT)"
    )
    con.commit()


def get_all_rows() -> list[InventoryRow]:
    con = connection()
    cur = con.cursor()
    cur.execute(f"SELECT {_SELECT_COLUMNS} FROM {TABLE_NAME} ORDER BY guid")
    return [_row(record) for record in cur.fetchall()]


def get_row(guid: str) -> InventoryRow | None:
    con = connection()
    cur = con.cursor()
    cur.execute(f"SELECT {_SELECT_COLUMNS} FROM {TABLE_NAME} WHERE guid = ?", (guid,))
    record = cur.fetchone()
    return _row(record) if record else None


def record_seen(guid: str, name: str | None, normalised_name: str | None, stamp: str):
    """Insert or stamp a row: ``first_seen`` is kept, ``last_seen`` advances."""
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"INSERT INTO {TABLE_NAME} "
        "(guid, name, normalised_name, first_seen, last_seen, read_count) "
        "VALUES (?, ?, ?, ?, ?, 1) "
        "ON CONFLICT(guid) DO UPDATE SET "
        "name = COALESCE(excluded.name, name), "
        "normalised_name = COALESCE(excluded.normalised_name, normalised_name), "
        "last_seen = excluded.last_seen, "
        "read_count = read_count + 1",
        (guid, name, normalised_name, stamp, stamp),
    )
    con.commit()


def set_notices(guid: str, notices_json: str | None) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"UPDATE {TABLE_NAME} SET notices_json = ? WHERE guid = ?", (notices_json, guid)
    )
    con.commit()


def delete_row(guid: str) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(f"DELETE FROM {TABLE_NAME} WHERE guid = ?", (guid,))
    con.commit()


if __name__ == "__main__":
    pass
