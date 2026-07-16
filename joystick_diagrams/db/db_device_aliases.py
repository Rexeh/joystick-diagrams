from joystick_diagrams.db.db_connection import connection


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS device_aliases(source_guid TEXT PRIMARY KEY, target_guid TEXT NOT NULL)"
    )
    connection().commit()


def add_update_alias(source_guid: str, target_guid: str):
    con = connection()
    cur = con.cursor()

    query = (
        "INSERT OR REPLACE INTO device_aliases (source_guid, target_guid) VALUES(?,?)"
    )
    params = (source_guid, target_guid)
    cur.execute(query, params)

    con.commit()


def get_all_aliases() -> list[tuple[str, str]]:
    con = connection()
    cur = con.cursor()

    cur.execute("SELECT source_guid, target_guid FROM device_aliases")
    return cur.fetchall()


def delete_alias(source_guid: str):
    con = connection()
    cur = con.cursor()

    cur.execute("DELETE FROM device_aliases WHERE source_guid = ?", [source_guid])
    con.commit()
