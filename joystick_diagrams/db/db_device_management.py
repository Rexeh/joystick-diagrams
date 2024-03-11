from joystick_diagrams.db.db_connection import connection

TABLE_NAME = "devices"


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()

    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(guid TEXT PRIMARY KEY, template_path TEXT)"
    )


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


if __name__ == "__main__":
    pass
