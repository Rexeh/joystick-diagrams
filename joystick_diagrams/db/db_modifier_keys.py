"""Persistence for the modifier key registry (groups and aliases).

Two tables with one style column:

- ``modifier_keys``: a group keyed by ``(kind, canonical)`` with its label,
  priority and style JSON. The composite key means a profile called "Shift"
  (a QUALIFIER) can never share a row with the real Shift key.
- ``modifier_key_aliases``: a normalised raw spelling -> canonical, with the
  group's kind, an optional display label and the ``side_alias`` flag that the
  "Treat left and right keys as the same" toggle reads at resolution time.

Seeding is the service's job (``modifier_key_service.py``); this module is CRUD only.
"""

from joystick_diagrams.db.db_connection import connection

KEYS_TABLE = "modifier_keys"
ALIASES_TABLE = "modifier_key_aliases"

# Row shapes returned by the getters, in column order.
ModifierKeyRow = tuple[str, str, str | None, int, str | None, int]
ModifierKeyAliasRow = tuple[str, str, str, str | None, int, int]


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {KEYS_TABLE}("
        "kind TEXT NOT NULL, "
        "canonical TEXT NOT NULL, "
        "display_label TEXT, "
        "priority INTEGER NOT NULL DEFAULT 100, "
        "style_json TEXT, "
        "builtin BOOLEAN NOT NULL DEFAULT 0, "
        "PRIMARY KEY (kind, canonical))"
    )
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {ALIASES_TABLE}("
        "alias TEXT PRIMARY KEY, "
        "canonical TEXT NOT NULL, "
        "kind TEXT NOT NULL DEFAULT 'KEY', "
        "display_label TEXT, "
        "side_alias BOOLEAN NOT NULL DEFAULT 0, "
        "builtin BOOLEAN NOT NULL DEFAULT 0)"
    )
    con.commit()


# ── Groups ─────────────────────────────────────────────────────────────


def upsert_modifier_key(row: ModifierKeyRow, *, replace: bool = True) -> None:
    """Insert or update a group row ``(kind, canonical, display_label, priority,
    style_json, builtin)``. ``replace=False`` keeps an existing row untouched."""
    kind, canonical, display_label, priority, style_json, builtin = row
    con = connection()
    cur = con.cursor()
    verb = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
    cur.execute(
        f"{verb} INTO {KEYS_TABLE} "
        "(kind, canonical, display_label, priority, style_json, builtin) "
        "VALUES (?,?,?,?,?,?)",
        (kind, canonical, display_label, int(priority), style_json, int(builtin)),
    )
    con.commit()


def get_all_modifier_keys() -> list[ModifierKeyRow]:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"SELECT kind, canonical, display_label, priority, style_json, builtin "
        f"FROM {KEYS_TABLE} ORDER BY priority, canonical"
    )
    return cur.fetchall()


def delete_modifier_key(kind: str, canonical: str) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"DELETE FROM {KEYS_TABLE} WHERE kind = ? AND canonical = ?", (kind, canonical)
    )
    con.commit()


# ── Aliases ────────────────────────────────────────────────────────────


def upsert_alias(row: ModifierKeyAliasRow, *, replace: bool = True) -> None:
    """Insert or update an alias row ``(alias, canonical, kind, display_label,
    side_alias, builtin)``. ``replace=False`` keeps an existing row untouched."""
    alias, canonical, kind, display_label, side_alias, builtin = row
    con = connection()
    cur = con.cursor()
    verb = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
    cur.execute(
        f"{verb} INTO {ALIASES_TABLE} "
        "(alias, canonical, kind, display_label, side_alias, builtin) "
        "VALUES (?,?,?,?,?,?)",
        (alias, canonical, kind, display_label, int(side_alias), int(builtin)),
    )
    con.commit()


def get_all_aliases() -> list[ModifierKeyAliasRow]:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"SELECT alias, canonical, kind, display_label, side_alias, builtin "
        f"FROM {ALIASES_TABLE} ORDER BY alias"
    )
    return cur.fetchall()


def delete_alias(alias: str) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(f"DELETE FROM {ALIASES_TABLE} WHERE alias = ?", (alias,))
    con.commit()


def delete_aliases_for_canonical(kind: str, canonical: str) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"DELETE FROM {ALIASES_TABLE} WHERE kind = ? AND canonical = ?",
        (kind, canonical),
    )
    con.commit()
