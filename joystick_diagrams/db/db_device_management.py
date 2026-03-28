import logging

from joystick_diagrams.db.db_connection import connection

_logger = logging.getLogger(__name__)

TABLE_NAME = "devices"


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()

    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(guid TEXT PRIMARY KEY, template_path TEXT, name TEXT, hidden BOOLEAN DEFAULT 0)"
    )

    # Migrate existing tables that lack the hidden/name columns
    _migrate_add_column(cur, "hidden", "BOOLEAN DEFAULT 0")
    _migrate_add_column(cur, "name", "TEXT")
    con.commit()


def _migrate_add_column(cursor, column_name: str, column_def: str):
    try:
        cursor.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column_name} {column_def}"
        )
    except Exception:
        pass  # Column already exists


def get_device_templates() -> list:
    con = connection()
    cur = con.cursor()

    cur.execute("SELECT * from devices")
    return cur.fetchall()


def remove_template_path_from_device(guid: str):
    con = connection()
    cur = con.cursor()
    cur.execute("UPDATE devices SET template_path = NULL WHERE guid =  ?", (guid,))
    connection().commit()


def add_update_device_template_path(guid: str, template_path: str) -> bool:
    con = connection()
    cur = con.cursor()

    cur.execute("SELECT * from devices WHERE guid = ?", (guid,))
    result = cur.fetchall()

    if result:
        query = "UPDATE devices SET template_path = ? WHERE guid =  ? "
        params = (template_path, guid)
        cur.execute(query, params)

    else:
        query = "INSERT INTO devices (guid, template_path) VALUES(?,?)"
        params = (guid, template_path)
        cur.execute(query, params)

    con.commit()
    return True


def get_device_template_path(guid: str):
    con = connection()
    cur = con.cursor()

    query = "SELECT template_path from devices WHERE guid = ?"
    params = [guid]

    cur.execute(query, params)
    result = cur.fetchone()

    return result[0] if result else None


def set_device_hidden(guid: str, name: str, hidden: bool):
    con = connection()
    cur = con.cursor()

    cur.execute("SELECT guid FROM devices WHERE guid = ?", (guid,))
    result = cur.fetchone()

    if result:
        cur.execute(
            "UPDATE devices SET hidden = ?, name = ? WHERE guid = ?",
            (int(hidden), name, guid),
        )
    else:
        cur.execute(
            "INSERT INTO devices (guid, name, hidden) VALUES (?, ?, ?)",
            (guid, name, int(hidden)),
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


if __name__ == "__main__":
    pass
