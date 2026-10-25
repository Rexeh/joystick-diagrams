"""Persistence for layout ops (plan §5.3). CRUD only; ``LayoutService`` owns
validation, caching and drift detection.

One row per ``(template_key, profile_key)``: ``profile_key = ''`` is the template
layer ("all profiles on this diagram"), otherwise it is
``ProfileWrapper.profile_key``. ``ops_json`` is ``LayoutDocument.model_dump_json()``
and carries its own ``schema_version``; ``content_hash`` is the template's
``Template.content_hash`` when the ops were last written, which the service
compares with the current file to notice template updates.
"""

from datetime import datetime, timezone

from joystick_diagrams.db.db_connection import connection

TABLE_NAME = "template_layouts"

# (template_key, profile_key, ops_json, content_hash, updated_at)
LayoutRow = tuple[str, str, str, str | None, str | None]


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}("
        "template_key TEXT NOT NULL, "
        "profile_key TEXT NOT NULL DEFAULT '', "
        "ops_json TEXT NOT NULL, "
        "content_hash TEXT, "
        "updated_at TEXT, "
        "PRIMARY KEY (template_key, profile_key))"
    )
    con.commit()


def upsert_layout(
    template_key: str, profile_key: str, ops_json: str, content_hash: str | None
) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"INSERT OR REPLACE INTO {TABLE_NAME} "
        "(template_key, profile_key, ops_json, content_hash, updated_at) "
        "VALUES (?,?,?,?,?)",
        (
            template_key,
            profile_key,
            ops_json,
            content_hash,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    con.commit()


def get_all_layouts() -> list[LayoutRow]:
    con = connection()
    cur = con.cursor()
    cur.execute(
        "SELECT template_key, profile_key, ops_json, content_hash, updated_at "
        f"FROM {TABLE_NAME} ORDER BY template_key, profile_key"
    )
    return cur.fetchall()


def get_layout(template_key: str, profile_key: str) -> LayoutRow | None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        "SELECT template_key, profile_key, ops_json, content_hash, updated_at "
        f"FROM {TABLE_NAME} WHERE template_key = ? AND profile_key = ?",
        (template_key, profile_key),
    )
    return cur.fetchone()


def delete_layout(template_key: str, profile_key: str) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"DELETE FROM {TABLE_NAME} WHERE template_key = ? AND profile_key = ?",
        (template_key, profile_key),
    )
    con.commit()


def delete_layouts_for_template(template_key: str) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(f"DELETE FROM {TABLE_NAME} WHERE template_key = ?", (template_key,))
    con.commit()


def rename_template_key(old_key: str, new_key: str) -> None:
    """Re-link every layer of ``old_key`` to ``new_key`` (the template moved)."""
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"UPDATE OR REPLACE {TABLE_NAME} SET template_key = ? WHERE template_key = ?",
        (new_key, old_key),
    )
    con.commit()


if __name__ == "__main__":
    pass
