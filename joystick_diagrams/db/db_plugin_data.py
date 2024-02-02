import os
from sqlite3 import connect

DB_DIR = "data"
DB_NAME = "joystick_diagrams.db"
TABLE_NAME = "plugins"


def create_new_db_if_not_exist():
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(plugin_name TEXT PRIMARY KEY, enabled BOOL)")


def add__update_plugin_configuration(plugin_name: str, enabled: bool):
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()

    query = "SELECT * from plugins WHERE plugin_name = ?"
    params = (plugin_name,)

    cur.execute(query, params)
    result = cur.fetchall()

    if result:
        query = "UPDATE plugins SET enabled = ? WHERE plugin_name =  ? "
        params = (enabled, plugin_name)
        cur.execute(query, params)

    else:
        query = "INSERT INTO plugins (plugin_name, enabled) VALUES(?,?)"
        params = (plugin_name, enabled)
        cur.execute(query, params)

    connection.commit()


def get_plugin_configuration(plugin_name: str):
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()

    query = "SELECT * from plugins WHERE plugin_name = ?"
    params = [plugin_name]

    cur.execute(query, params)
    result = cur.fetchone()

    return result if result else None


if __name__ == "__main__":
    pass
