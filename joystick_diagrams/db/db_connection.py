import os
from sqlite3 import Connection, connect

DB_DIR = "data"
DB_NAME = "joystick_diagrams.db"


def connection() -> Connection:
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    return connection
