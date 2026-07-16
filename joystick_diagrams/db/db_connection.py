from sqlite3 import Connection, connect

from joystick_diagrams.utils import data_root

DB_DIR = "data"
DB_NAME = "joystick_diagrams.db"


def connection() -> Connection:
    path = data_root().joinpath(DB_DIR, DB_NAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(str(path))
    return connection
