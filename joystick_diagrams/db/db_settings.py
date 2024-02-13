import os
from sqlite3 import connect

DB_DIR = "data"
DB_NAME = "joystick_diagrams.db"


def create_new_db_if_not_exist():
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS settings(setting_key TEXT PRIMARY KEY, value TEXT)"
    )
    connection.commit()


def add_update_setting_value(setting_key: str, value: str):
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()
    params = (setting_key, value)
    query = """
    INSERT OR REPLACE into settings (setting_key, value) VALUES (?,?)
    """
    cur.execute(query, params)
    connection.commit()


def get_setting(setting_key: str) -> str | None:
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()
    params = (setting_key,)
    query = """
    SELECT VALUE FROM settings where setting_key = ?
    """
    cur.execute(query, params)
    _data = cur.fetchone()

    return _data[0] if _data else None


if __name__ == "__main__":
    pass
