from joystick_diagrams.db.db_connection import connection


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS settings(setting_key TEXT PRIMARY KEY, value TEXT)"
    )
    con.commit()


def add_update_setting_value(setting_key: str, value: str):
    con = connection()
    cur = con.cursor()
    params = (setting_key, value)
    query = """
    INSERT OR REPLACE into settings (setting_key, value) VALUES (?,?)
    """
    cur.execute(query, params)
    con.commit()


def get_setting(setting_key: str) -> str | None:
    con = connection()
    cur = con.cursor()
    params = (setting_key,)
    query = """
    SELECT VALUE FROM settings where setting_key = ?
    """
    cur.execute(query, params)
    _data = cur.fetchone()

    return _data[0] if _data else None


if __name__ == "__main__":
    pass
