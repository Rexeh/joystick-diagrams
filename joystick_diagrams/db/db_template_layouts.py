"""Persistence for layout ops (plan §5.3). CRUD only; ``LayoutService`` owns
validation, caching and drift detection.

One row per ``(template_key, device_guid, profile_key)``:

- ``device_guid`` is the controller the edits belong to, so two controllers that
  share a template (two Starter Template copies, say) keep independent layouts.
  ``device_guid = ''`` (``ALL_DEVICES``) is the shared layer: "every controller
  that uses this template". Readers prefer a controller's own layer and fall
  back to the shared one, layer by layer (see ``LayoutService.get_layers``).
- ``profile_key = ''`` is the template layer ("all profiles on this diagram"),
  otherwise it is ``ProfileWrapper.profile_key``.

``ops_json`` is ``LayoutDocument.model_dump_json()`` and carries its own
``schema_version``; ``content_hash`` is the template's ``Template.content_hash``
when the ops were last written, which the service compares with the current
file to notice template updates.

Migration: tables created before ``device_guid`` existed are rebuilt. Every old
row is copied once per controller that currently uses that template (from the
``devices`` table, which ``db_handler.init`` migrates first); a row whose
template no controller uses is kept as the shared layer so nothing is lost.
"""

import sqlite3
from datetime import datetime, timezone

from joystick_diagrams.db.db_connection import connection

TABLE_NAME = "template_layouts"
LEGACY_TABLE_NAME = "template_layouts_legacy"
ALL_DEVICES = ""  # device_guid of the shared "every controller on this template" layer

# (template_key, device_guid, profile_key, ops_json, content_hash, updated_at)
LayoutRow = tuple[str, str, str, str, str | None, str | None]

_COLUMNS = "template_key, device_guid, profile_key, ops_json, content_hash, updated_at"


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    if _table_exists(cur, TABLE_NAME) and not _has_column(
        cur, TABLE_NAME, "device_guid"
    ):
        cur.execute(f"ALTER TABLE {TABLE_NAME} RENAME TO {LEGACY_TABLE_NAME}")
    _create_table(cur)
    if _table_exists(cur, LEGACY_TABLE_NAME):
        _migrate_legacy_rows(cur)
        cur.execute(f"DROP TABLE {LEGACY_TABLE_NAME}")
    con.commit()


def _create_table(cur) -> None:
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}("
        "template_key TEXT NOT NULL, "
        "device_guid TEXT NOT NULL DEFAULT '', "
        "profile_key TEXT NOT NULL DEFAULT '', "
        "ops_json TEXT NOT NULL, "
        "content_hash TEXT, "
        "updated_at TEXT, "
        "PRIMARY KEY (template_key, device_guid, profile_key))"
    )


def _table_exists(cur, name: str) -> bool:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    )
    return cur.fetchone() is not None


def _has_column(cur, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def _devices_using(cur, template_key: str) -> list[str]:
    try:
        cur.execute(
            "SELECT guid FROM devices WHERE template_key = ? ORDER BY guid",
            (template_key,),
        )
    except sqlite3.OperationalError:  # no devices table in this database
        return []
    return [row[0] for row in cur.fetchall()]


def _migrate_legacy_rows(cur) -> None:
    cur.execute(
        "SELECT template_key, profile_key, ops_json, content_hash, updated_at "
        f"FROM {LEGACY_TABLE_NAME}"
    )
    for template_key, profile_key, ops_json, content_hash, updated_at in cur.fetchall():
        targets = _devices_using(cur, template_key) or [ALL_DEVICES]
        for device_guid in targets:
            cur.execute(
                f"INSERT OR REPLACE INTO {TABLE_NAME} ({_COLUMNS}) VALUES (?,?,?,?,?,?)",
                (
                    template_key,
                    device_guid,
                    profile_key,
                    ops_json,
                    content_hash,
                    updated_at,
                ),
            )


def upsert_layout(
    template_key: str,
    profile_key: str,
    ops_json: str,
    content_hash: str | None,
    device_guid: str = ALL_DEVICES,
) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"INSERT OR REPLACE INTO {TABLE_NAME} ({_COLUMNS}) VALUES (?,?,?,?,?,?)",
        (
            template_key,
            device_guid,
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
        f"SELECT {_COLUMNS} FROM {TABLE_NAME} "
        "ORDER BY template_key, device_guid, profile_key"
    )
    return cur.fetchall()


def get_layout(
    template_key: str, profile_key: str, device_guid: str = ALL_DEVICES
) -> LayoutRow | None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"SELECT {_COLUMNS} FROM {TABLE_NAME} "
        "WHERE template_key = ? AND device_guid = ? AND profile_key = ?",
        (template_key, device_guid, profile_key),
    )
    return cur.fetchone()


def delete_layout(
    template_key: str, profile_key: str, device_guid: str = ALL_DEVICES
) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"DELETE FROM {TABLE_NAME} "
        "WHERE template_key = ? AND device_guid = ? AND profile_key = ?",
        (template_key, device_guid, profile_key),
    )
    con.commit()


def delete_layouts_for_template(
    template_key: str, device_guid: str | None = None
) -> None:
    """Delete every layer of ``template_key`` (for one controller when given)."""
    con = connection()
    cur = con.cursor()
    if device_guid is None:
        cur.execute(f"DELETE FROM {TABLE_NAME} WHERE template_key = ?", (template_key,))
    else:
        cur.execute(
            f"DELETE FROM {TABLE_NAME} WHERE template_key = ? AND device_guid = ?",
            (template_key, device_guid),
        )
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


def copy_device_layers(template_key: str, from_guid: str, to_guid: str) -> int:
    """Copy every layer of ``(template_key, from_guid)`` to ``to_guid``; returns the count."""
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"INSERT OR REPLACE INTO {TABLE_NAME} ({_COLUMNS}) "
        "SELECT template_key, ?, profile_key, ops_json, content_hash, ? "
        f"FROM {TABLE_NAME} WHERE template_key = ? AND device_guid = ?",
        (to_guid, datetime.now(timezone.utc).isoformat(), template_key, from_guid),
    )
    count = cur.rowcount
    con.commit()
    return count


if __name__ == "__main__":
    pass
