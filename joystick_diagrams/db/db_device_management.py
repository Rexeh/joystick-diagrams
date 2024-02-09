import os
from sqlite3 import connect

DB_DIR = "data"
DB_NAME = "joystick_diagrams.db"
TABLE_NAME = "devices"


def create_new_db_if_not_exist():
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(guid TEXT PRIMARY KEY, template_path TEXT)"
    )


def get_device_templates() -> list:
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()

    cur.execute("SELECT * from devices")
    return cur.fetchall()


def add_update_device_template_path(guid: str, template_path: str) -> bool:
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()

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

    connection.commit()
    return True


def get_device_template_path(guid: str):
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()

    query = "SELECT template_path from devices WHERE guid = ?"
    params = [guid]

    cur.execute(query, params)
    result = cur.fetchone()

    return result[0] if result else None


if __name__ == "__main__":
    add_update_device_template_path("123", "2322323")
    data = get_device_template_path("1234")
    print(data)
