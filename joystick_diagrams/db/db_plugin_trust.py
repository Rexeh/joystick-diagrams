"""Plugin trust state persistence.

Tracks which user-installed plugins have been trusted by the user
or verified via developer signature.
"""

from datetime import datetime, timezone

from joystick_diagrams.db.db_connection import connection

TABLE_NAME = "plugin_trust"


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}"
        "(plugin_name TEXT, plugin_type TEXT, trusted BOOL NOT NULL DEFAULT 0, "
        "trust_reason TEXT, trusted_at TEXT, "
        "PRIMARY KEY (plugin_name, plugin_type))"
    )


def is_plugin_trusted(plugin_name: str, plugin_type: str) -> bool:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"SELECT trusted FROM {TABLE_NAME} WHERE plugin_name = ? AND plugin_type = ?",
        (plugin_name, plugin_type),
    )
    result = cur.fetchone()
    return bool(result and result[0])


def set_plugin_trusted(
    plugin_name: str, plugin_type: str, trusted: bool, reason: str
) -> None:
    con = connection()
    cur = con.cursor()
    now = datetime.now(timezone.utc).isoformat()

    cur.execute(
        f"SELECT * FROM {TABLE_NAME} WHERE plugin_name = ? AND plugin_type = ?",
        (plugin_name, plugin_type),
    )
    result = cur.fetchone()

    if result:
        cur.execute(
            f"UPDATE {TABLE_NAME} SET trusted = ?, trust_reason = ?, trusted_at = ? "
            "WHERE plugin_name = ? AND plugin_type = ?",
            (trusted, reason, now, plugin_name, plugin_type),
        )
    else:
        cur.execute(
            f"INSERT INTO {TABLE_NAME} "
            "(plugin_name, plugin_type, trusted, trust_reason, trusted_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (plugin_name, plugin_type, trusted, reason, now),
        )

    con.commit()


def remove_trust(plugin_name: str, plugin_type: str) -> None:
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"DELETE FROM {TABLE_NAME} WHERE plugin_name = ? AND plugin_type = ?",
        (plugin_name, plugin_type),
    )
    con.commit()


def get_trust_reason(plugin_name: str, plugin_type: str) -> str | None:
    """Get the trust reason for a plugin, or None if not trusted."""
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"SELECT trust_reason FROM {TABLE_NAME} "
        "WHERE plugin_name = ? AND plugin_type = ? AND trusted = 1",
        (plugin_name, plugin_type),
    )
    result = cur.fetchone()
    return result[0] if result else None
