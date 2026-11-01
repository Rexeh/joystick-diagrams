"""Persistence for combined pages. CRUD only; ``PageService`` owns validation,
caching and the model (``render/page.py``).

One row per page. ``placements_json`` is the list of ``Placement`` rows keyed by
``device_guid``; ``ops_json`` holds everything else that is not a column
(gaps, margin, scale, title, date, notes) so later fields need no migration.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from joystick_diagrams.db.db_connection import connection

TABLE_NAME = "pages"

# (page_id, name, size_preset, width_mm, height_mm, orientation, arrangement,
#  placements_json, ops_json, export_members_separately, updated_at, profile_rule)
PageRow = tuple[
    str, str, str, float | None, float | None, str, str, str, str, int, str | None, str
]

_COLUMNS = (
    "page_id, name, size_preset, width_mm, height_mm, orientation, arrangement, "
    "placements_json, ops_json, export_members_separately, updated_at, profile_rule"
)
DEFAULT_PROFILE_RULE = "shared"


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}("
        "page_id TEXT PRIMARY KEY, "
        "name TEXT NOT NULL, "
        "size_preset TEXT NOT NULL, "
        "width_mm REAL, "
        "height_mm REAL, "
        "orientation TEXT NOT NULL, "
        "arrangement TEXT NOT NULL, "
        "placements_json TEXT NOT NULL, "
        "ops_json TEXT NOT NULL, "
        "export_members_separately INTEGER NOT NULL DEFAULT 0, "
        "updated_at TEXT, "
        f"profile_rule TEXT NOT NULL DEFAULT '{DEFAULT_PROFILE_RULE}')"
    )
    # Pages made before the profile rule existed get the default ("shared")
    try:
        cur.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN profile_rule TEXT NOT NULL "
            f"DEFAULT '{DEFAULT_PROFILE_RULE}'"
        )
    except Exception:  # noqa: BLE001 - the column already exists
        pass
    con.commit()


@dataclass(frozen=True)
class PageRecord:
    """The columns of one page row, minus ``updated_at`` (written on upsert)."""

    page_id: str
    name: str
    size_preset: str
    width_mm: float | None
    height_mm: float | None
    orientation: str
    arrangement: str
    placements_json: str
    ops_json: str
    export_members_separately: bool
    profile_rule: str = DEFAULT_PROFILE_RULE


def upsert_page(record: PageRecord) -> str:
    """Insert or replace a page; returns the ``updated_at`` timestamp written."""
    updated_at = datetime.now(timezone.utc).isoformat()
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"INSERT OR REPLACE INTO {TABLE_NAME} ({_COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            record.page_id,
            record.name,
            record.size_preset,
            record.width_mm,
            record.height_mm,
            record.orientation,
            record.arrangement,
            record.placements_json,
            record.ops_json,
            1 if record.export_members_separately else 0,
            updated_at,
            record.profile_rule,
        ),
    )
    con.commit()
    return updated_at


def get_all_pages() -> list[PageRow]:
    con = connection()
    cur = con.cursor()
    cur.execute(f"SELECT {_COLUMNS} FROM {TABLE_NAME} ORDER BY name")
    return cur.fetchall()


def get_page(page_id: str) -> PageRow | None:
    con = connection()
    cur = con.cursor()
    cur.execute(f"SELECT {_COLUMNS} FROM {TABLE_NAME} WHERE page_id = ?", (page_id,))
    return cur.fetchone()


def delete_page(page_id: str) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(f"DELETE FROM {TABLE_NAME} WHERE page_id = ?", (page_id,))
    con.commit()


if __name__ == "__main__":
    pass
