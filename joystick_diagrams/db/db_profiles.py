from joystick_diagrams.db.db_connection import connection

TABLE_NAME = "profiles"


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(profile_key TEXT PRIMARY KEY)"
    )


def get_profile(profile_key: str) -> list[str]:
    con = connection()
    cur = con.cursor()

    query = "SELECT * from profiles WHERE profile_key = ?"
    params = (profile_key,)

    cur.execute(query, params)
    result = cur.fetchone()

    if not result:
        return add_profile(profile_key)

    return result[0]


def add_profile(profile_key: str) -> list[str]:
    con = connection()
    cur = con.cursor()

    query = "INSERT OR IGNORE INTO profiles (profile_key) VALUES(?)"
    params = (profile_key,)
    cur.execute(query, params)

    con.commit()

    query = "SELECT * from profiles WHERE profile_key = ?"
    params = (profile_key,)

    cur.execute(query, params)
    result = cur.fetchall()
    return result[0]


def get_profile_parents(profile_key: str):
    con = connection()
    cur = con.cursor()

    query = "SELECT parent_profile_key,ordering from profile_parents WHERE profile_key = ? ORDER BY ordering asc"
    params = (profile_key,)

    cur.execute(query, params)
    result = cur.fetchall()

    return result


if __name__ == "__main__":
    create_new_db_if_not_exist()

    data = get_profile_parents("my_profile_key")
    print(data)
