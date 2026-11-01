"""Persistence for user-created styles (themes). CRUD only; ``ThemeService`` owns
validation, caching and the built-ins (which are never stored).

``theme_json`` is ``Theme.model_dump_json()`` and carries its own
``schema_version`` so sharing/import can be added later without a migration.
"""

from datetime import datetime, timezone

from joystick_diagrams.db.db_connection import connection

TABLE_NAME = "themes"

# (theme_id, name, theme_json, updated_at)
ThemeRow = tuple[str, str, str, str | None]


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}("
        "theme_id TEXT PRIMARY KEY, "
        "name TEXT NOT NULL, "
        "theme_json TEXT NOT NULL, "
        "updated_at TEXT)"
    )
    con.commit()


def upsert_theme(theme_id: str, name: str, theme_json: str) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"INSERT OR REPLACE INTO {TABLE_NAME} (theme_id, name, theme_json, updated_at) "
        "VALUES (?,?,?,?)",
        (theme_id, name, theme_json, datetime.now(timezone.utc).isoformat()),
    )
    con.commit()


def get_all_themes() -> list[ThemeRow]:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"SELECT theme_id, name, theme_json, updated_at FROM {TABLE_NAME} ORDER BY name"
    )
    return cur.fetchall()


def delete_theme(theme_id: str) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(f"DELETE FROM {TABLE_NAME} WHERE theme_id = ?", (theme_id,))
    con.commit()


if __name__ == "__main__":
    pass
