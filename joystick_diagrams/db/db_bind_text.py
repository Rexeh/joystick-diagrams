from joystick_diagrams.db.db_connection import connection


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS bind_text(original_str TEXT PRIMARY KEY, replaced_str TEXT)"
    )
    connection().commit()


def add_update_bind_text(original_str: str, replaced_str: str):
    con = connection()
    cur = con.cursor()

    query = "SELECT * from bind_text WHERE original_str = ?"
    params = [
        original_str,
    ]

    cur.execute(query, params)
    result = cur.fetchall()

    if result:
        query = "UPDATE bind_text SET replaced_str = ? WHERE original_str =  ?"
        params = (replaced_str, original_str)
        cur.execute(query, params)

    else:
        query = "INSERT INTO bind_text (original_str, replaced_str) VALUES(?,?)"
        params = (original_str, replaced_str)
        cur.execute(query, params)

    con.commit()


def get_bind_text_for_string(search_string: str) -> str | None:
    con = connection()
    cur = con.cursor()

    query = "SELECT replaced_str from bind_text WHERE original_str = ?"
    params = [search_string]

    cur.execute(query, params)
    result = cur.fetchone()

    if not result:
        return None

    return result[0]


if __name__ == "__main__":
    create_new_db_if_not_exist()
    add_update_bind_text("123", "2322323")
    value = get_bind_text_for_string("123")
