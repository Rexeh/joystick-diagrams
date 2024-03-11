from joystick_diagrams.db.db_connection import connection

TABLE_NAME = "plugins"


def create_new_db_if_not_exist():
    con = connection()
    cur = con.cursor()
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(plugin_name TEXT PRIMARY KEY, enabled BOOL)"
    )


def add__update_plugin_configuration(plugin_name: str, enabled: bool):
    con = connection()
    cur = con.cursor()

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

    con.commit()


def get_plugin_configuration(plugin_name: str):
    con = connection()
    cur = con.cursor()

    query = "SELECT * from plugins WHERE plugin_name = ?"
    params = [plugin_name]

    cur.execute(query, params)
    result = cur.fetchone()

    return result if result else None


if __name__ == "__main__":
    pass
