import logging
import os
import sqlite3
from sqlite3 import connect

DB_DIR = "data"
DB_NAME = "joystick_diagrams.db"
TABLE_NAME = "profile_parents"

_logger = logging.getLogger(__name__)


def create_new_db_if_not_exist():
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    connection.execute("PRAGMA foreign_keys = 1")
    cur = connection.cursor()
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(\
            parent_profile_key TEXT NOT NULL,\
            ordering INT NOT NULL,\
            profile_key TEXT NOT NULL,\
            PRIMARY KEY(parent_profile_key, profile_key),\
            FOREIGN KEY(profile_key) REFERENCES profiles(profile_key) \
            )"
    )


def add_parents_to_profile(profile_key: str, parents: list):
    path = os.path.join(os.getcwd(), DB_DIR, DB_NAME)
    connection = connect(path)
    connection.execute("PRAGMA foreign_keys = 1")
    cur = connection.cursor()

    query = "SELECT * from profiles WHERE profile_key = ?"
    params = (profile_key,)

    cur.execute(query, params)
    result = cur.fetchone()

    if not result:
        _logger.error(
            f"Tried to add a parent to a profile that does not exist in the DB {profile_key=}, and {parents=}"
        )

    if result:
        # Delete existing relationships
        query = "DELETE FROM profile_parents where profile_key = ?"
        params = (profile_key,)
        cur.execute(query, params)

        try:
            for index, parent in enumerate(parents, 1):
                query = "INSERT INTO profile_parents (parent_profile_key, ordering, profile_key) VALUES(?,?,?)"
                params = (parent, index, result[0])
                cur.execute(query, params)

        except sqlite3.IntegrityError:
            _logger.error(
                f"Integrity errors when inserting which suggests the {profile_key=} no longer exists in profiles"
            )

    connection.commit()


if __name__ == "__main__":
    create_new_db_if_not_exist()

    add_parents_to_profile("my_profile_key", ["profile_parent_1", "profile_parent_2"])
