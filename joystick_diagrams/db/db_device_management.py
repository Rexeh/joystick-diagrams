import os
from sqlite3 import connect

DB_DIR = "data"
DB_NAME = "devices.db"
TABLE_NAME = "devices"


def create_new_db_if_not_exist():
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(guid TEXT PRIMARY KEY, template_path TEXT)")


def add_update_device_template_path(guid: str, template_path: str):
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()

    cur.execute(f"SELECT * from {TABLE_NAME} WHERE guid = {guid}")
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


if __name__ == "__main__":
    add_update_device_template_path("123", "2322323")
