"""Handles initialistion of DB for Joystick Diagrams.

Author: Robert Cox
"""

from db import db_device_management

from joystick_diagrams.db import db_value_store


def init():
    db_device_management.create_new_db_if_not_exist()
    db_value_store.create_new_db_if_not_exist()


if __name__ == "__main__":
    init()
