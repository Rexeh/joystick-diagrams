"""The ``devices`` table: one row per controller GUID the app has seen or configured.

Columns (all added with the ad-hoc ``ALTER TABLE`` migration pattern so older
databases upgrade in place):

- ``template_path`` / ``template_key`` / ``template_hash``: the chosen template.
  ``template_key`` is the stable identity (``bundled:<relpath>`` or
  ``user:<abs>``, see ``template.template_key_for``) and ``template_hash`` the
  sha256 of the file when it was chosen; both let ``template_identity`` relink a
  moved file instead of forgetting the choice.
- ``kind`` / ``kind_source`` / ``kind_reason``: the controller's classification
  (``joystick``/``keyboard``/``mouse``/``gamepad``/``other``). ``other``,
  ``keyboard`` and ``mouse`` mean **No diagram** (``NO_DIAGRAM_KINDS``). ``kind_source`` is ``'user'`` (the
  "Make a diagram for this controller" checkbox; never overwritten by the app)
  or ``'auto'`` (recomputed on every read from one fact: nothing bound).
  ``kind_reason`` is a machine code (``nothing_bound``, ``nothing_bound_moved``,
  ``user``, ``legacy_hidden``); ``device_status.reason_text`` turns it into words.
- ``hidden``: legacy flag kept in sync with ``kind == 'other'`` for old code paths.
- ``last_seen`` (ISO-8601 UTC) and ``games_json`` (``{"<game>": <profile count>}``)
  come from the inventory snapshot taken after each read.
- ``name`` / ``custom_name``: the game's name for the device and the user's.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from joystick_diagrams.db.db_connection import connection

_logger = logging.getLogger(__name__)

TABLE_NAME = "devices"

KIND_OTHER = "other"  # "No diagram" (user choice or nothing bound)
# Kinds that get no diagram: the user's "other", or a game-declared keyboard/mouse.
NO_DIAGRAM_KINDS = frozenset({KIND_OTHER, "keyboard", "mouse"})
KIND_SOURCE_USER = "user"
KIND_SOURCE_AUTO = "auto"
KIND_REASON_LEGACY_HIDDEN = "legacy_hidden"

COLUMNS = (
    "guid",
    "template_path",
    "name",
    "hidden",
    "custom_name",
    "kind",
    "kind_source",
    "kind_reason",
    "last_seen",
    "games_json",
    "template_key",
    "template_hash",
)
_SELECT_COLUMNS = ", ".join(COLUMNS)


@dataclass(frozen=True)
class DeviceRow:
    guid: str
    template_path: str | None = None
    name: str | None = None
    hidden: bool = False
    custom_name: str | None = None
    kind: str | None = None
    kind_source: str | None = None
    kind_reason: str | None = None
    last_seen: str | None = None
    games_json: str | None = None
    template_key: str | None = None
    template_hash: str | None = None

    @property
    def games(self) -> dict[str, int]:
        if not self.games_json:
            return {}
        try:
            data = json.loads(self.games_json)
        except ValueError:
            return {}
        return (
            {str(k): int(v) for k, v in data.items()} if isinstance(data, dict) else {}
        )


def _row(record) -> DeviceRow:
    values = dict(zip(COLUMNS, record, strict=True))
    values["hidden"] = bool(values["hidden"])
    return DeviceRow(**values)


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()

    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(guid TEXT PRIMARY KEY, template_path TEXT, name TEXT, hidden BOOLEAN DEFAULT 0)"
    )

    # Migrate existing tables that lack the newer columns
    _migrate_add_column(cur, "hidden", "BOOLEAN DEFAULT 0")
    _migrate_add_column(cur, "name", "TEXT")
    _migrate_add_column(cur, "custom_name", "TEXT")
    _migrate_add_column(cur, "kind", "TEXT")
    _migrate_add_column(cur, "kind_source", "TEXT")
    _migrate_add_column(cur, "kind_reason", "TEXT")
    _migrate_add_column(cur, "last_seen", "TEXT")
    _migrate_add_column(cur, "games_json", "TEXT")
    _migrate_add_column(cur, "template_key", "TEXT")
    _migrate_add_column(cur, "template_hash", "TEXT")
    _migrate_legacy_hidden(cur)
    _migrate_template_keys(cur)
    con.commit()


def _migrate_add_column(cursor, column_name: str, column_def: str):
    try:
        cursor.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column_name} {column_def}"
        )
    except Exception:
        pass  # Column already exists


def _migrate_legacy_hidden(cursor) -> None:
    """``hidden = 1`` rows from before ``kind`` existed become a user "No diagram"."""
    cursor.execute(
        f"UPDATE {TABLE_NAME} SET kind = ?, kind_source = ?, kind_reason = ? "
        "WHERE hidden = 1 AND kind IS NULL",
        (KIND_OTHER, KIND_SOURCE_USER, KIND_REASON_LEGACY_HIDDEN),
    )


def _migrate_template_keys(cursor) -> None:
    """Fill ``template_key``/``template_hash`` for rows that only have a path."""
    cursor.execute(
        f"SELECT guid, template_path FROM {TABLE_NAME} "
        "WHERE template_path IS NOT NULL AND template_path != '' AND template_key IS NULL"
    )
    for guid, template_path in cursor.fetchall():
        key, digest = template_identity_for_path(template_path)
        cursor.execute(
            f"UPDATE {TABLE_NAME} SET template_key = ?, template_hash = ? WHERE guid = ?",
            (key, digest, guid),
        )


def template_identity_for_path(
    template_path: str | None,
) -> tuple[str | None, str | None]:
    """``(template_key, sha256)`` for a path; the hash is ``None`` when unreadable."""
    from joystick_diagrams.template import hash_file_bytes, template_key_for

    if not template_path:
        return None, None
    path = Path(template_path)
    key = template_key_for(path)
    try:
        digest = hash_file_bytes(path)
    except OSError:
        digest = None
    return key, digest


def _ensure_row(cursor, guid: str) -> None:
    cursor.execute(f"INSERT OR IGNORE INTO {TABLE_NAME} (guid) VALUES (?)", (guid,))


# ── Rows ──


def get_device_templates() -> list:
    con = connection()
    cur = con.cursor()

    cur.execute("SELECT * from devices")
    return cur.fetchall()


def get_device_row(guid: str) -> DeviceRow | None:
    con = connection()
    cur = con.cursor()
    cur.execute(f"SELECT {_SELECT_COLUMNS} FROM {TABLE_NAME} WHERE guid = ?", (guid,))
    record = cur.fetchone()
    return _row(record) if record else None


def get_all_device_rows() -> list[DeviceRow]:
    con = connection()
    cur = con.cursor()
    cur.execute(f"SELECT {_SELECT_COLUMNS} FROM {TABLE_NAME} ORDER BY guid")
    return [_row(record) for record in cur.fetchall()]


# ── Template ──


def remove_template_path_from_device(guid: str):
    con = connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE devices SET template_path = NULL, template_key = NULL, "
        "template_hash = NULL WHERE guid = ?",
        (guid,),
    )
    con.commit()


def add_update_device_template_path(guid: str, template_path: str) -> bool:
    """Store the chosen template for ``guid`` (an empty path clears it).

    ``template_key`` and ``template_hash`` are derived from the path so every
    caller that still writes a bare path keeps the identity columns in step.
    """
    key, digest = template_identity_for_path(template_path)
    set_device_template(guid, template_path or None, key, digest)
    return True


def set_device_template(
    guid: str,
    template_path: str | None,
    template_key: str | None,
    template_hash: str | None,
) -> None:
    con = connection()
    cur = con.cursor()
    _ensure_row(cur, guid)
    cur.execute(
        f"UPDATE {TABLE_NAME} SET template_path = ?, template_key = ?, "
        "template_hash = ? WHERE guid = ?",
        (template_path, template_key, template_hash, guid),
    )
    con.commit()


def get_device_template_path(guid: str):
    con = connection()
    cur = con.cursor()

    query = "SELECT template_path from devices WHERE guid = ?"
    params = [guid]

    cur.execute(query, params)
    result = cur.fetchone()

    return result[0] if result else None


def get_devices_for_template_key(template_key: str) -> list[str]:
    """GUIDs of every device whose chosen template is ``template_key``."""
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"SELECT guid FROM {TABLE_NAME} WHERE template_key = ? ORDER BY guid",
        (template_key,),
    )
    return [row[0] for row in cur.fetchall()]


# ── Kind ("No diagram") ──


def set_device_kind(
    guid: str,
    kind: str | None,
    kind_source: str | None,
    kind_reason: str | None,
    name: str | None = None,
) -> None:
    """Write the classification; ``hidden`` follows ``kind in NO_DIAGRAM_KINDS``."""
    con = connection()
    cur = con.cursor()
    _ensure_row(cur, guid)
    cur.execute(
        f"UPDATE {TABLE_NAME} SET kind = ?, kind_source = ?, kind_reason = ?, "
        "hidden = ?, name = COALESCE(?, name) WHERE guid = ?",
        (kind, kind_source, kind_reason, int(kind in NO_DIAGRAM_KINDS), name, guid),
    )
    con.commit()


def get_device_kind(guid: str) -> tuple[str | None, str | None, str | None] | None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"SELECT kind, kind_source, kind_reason FROM {TABLE_NAME} WHERE guid = ?",
        (guid,),
    )
    return cur.fetchone()


def set_device_hidden(guid: str, name: str, hidden: bool):
    """Legacy entry point: hiding is a user "No diagram"; unhiding clears a user one."""
    if hidden:
        set_device_kind(guid, KIND_OTHER, KIND_SOURCE_USER, "user", name)
        return
    current = get_device_kind(guid)
    if current is not None and current[0] in NO_DIAGRAM_KINDS:
        set_device_kind(guid, None, None, None, name)
        return
    con = connection()
    cur = con.cursor()
    _ensure_row(cur, guid)
    cur.execute(
        f"UPDATE {TABLE_NAME} SET hidden = 0, name = COALESCE(?, name) WHERE guid = ?",
        (name, guid),
    )
    con.commit()


def get_hidden_devices() -> list[tuple[str, str]]:
    """Returns list of (guid, name) for all hidden devices."""
    con = connection()
    cur = con.cursor()
    cur.execute("SELECT guid, name FROM devices WHERE hidden = 1")
    return cur.fetchall()


def is_device_hidden(guid: str) -> bool:
    con = connection()
    cur = con.cursor()
    cur.execute("SELECT hidden FROM devices WHERE guid = ?", (guid,))
    result = cur.fetchone()
    return bool(result and result[0])


# ── Seen / games ──


def set_device_seen(
    guid: str, name: str | None, last_seen: str, games: dict[str, int]
) -> None:
    con = connection()
    cur = con.cursor()
    _ensure_row(cur, guid)
    cur.execute(
        f"UPDATE {TABLE_NAME} SET last_seen = ?, games_json = ?, "
        "name = COALESCE(?, name) WHERE guid = ?",
        (last_seen, json.dumps(games, sort_keys=True), name, guid),
    )
    con.commit()


# ── Custom names ──


def set_device_custom_name(guid: str, custom_name: str | None):
    """Set or clear a custom display name for a device."""
    con = connection()
    cur = con.cursor()
    _ensure_row(cur, guid)
    cur.execute(
        "UPDATE devices SET custom_name = ? WHERE guid = ?",
        (custom_name, guid),
    )
    con.commit()


def get_device_custom_name(guid: str) -> str | None:
    con = connection()
    cur = con.cursor()
    cur.execute("SELECT custom_name FROM devices WHERE guid = ?", (guid,))
    result = cur.fetchone()
    return result[0] if result and result[0] else None


def get_all_device_custom_names() -> dict[str, str]:
    """Returns dict of guid -> custom_name for all devices with custom names."""
    con = connection()
    cur = con.cursor()
    cur.execute("SELECT guid, custom_name FROM devices WHERE custom_name IS NOT NULL")
    return {row[0]: row[1] for row in cur.fetchall()}


if __name__ == "__main__":
    pass
