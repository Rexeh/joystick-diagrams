import os
from sqlite3 import connect

DB_DIR = "data"
DB_NAME = "joystick_diagrams.db"
TABLE_NAME = "profiles"


def create_new_db_if_not_exist():
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(profile_key TEXT PRIMARY KEY)"
    )


def get_profile(profile_key: str) -> list[str]:
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()

    query = "SELECT * from profiles WHERE profile_key = ?"
    params = (profile_key,)

    cur.execute(query, params)
    result = cur.fetchone()

    if not result:
        return add_profile(profile_key)

    return result[0]


def add_profile(profile_key: str) -> list[str]:
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()

    query = "INSERT OR IGNORE INTO profiles (profile_key) VALUES(?)"
    params = (profile_key,)
    cur.execute(query, params)

    connection.commit()

    query = "SELECT * from profiles WHERE profile_key = ?"
    params = (profile_key,)

    cur.execute(query, params)
    result = cur.fetchall()
    return result[0]


def get_profile_parents(profile_key: str):
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    cur = connection.cursor()

    query = "SELECT parent_profile_key,ordering from profile_parents WHERE profile_key = ? ORDER BY ordering asc"
    params = (profile_key,)

    cur.execute(query, params)
    result = cur.fetchall()

    return result


if __name__ == "__main__":
    create_new_db_if_not_exist()

    data = get_profile_parents("my_profile_key")
    print(data)
