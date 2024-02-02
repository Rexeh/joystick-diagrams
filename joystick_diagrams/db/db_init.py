"""Handles initialistion of DB for Joystick Diagrams.

Author: Robert Cox
"""

import logging

from joystick_diagrams.db import db_device_management, db_plugin_data, db_value_store

_logger = logging.getLogger(__name__)


def init() -> None:
    _logger.info("Initialising datastores")
    db_device_management.create_new_db_if_not_exist()
    db_value_store.create_new_db_if_not_exist()
    db_plugin_data.create_new_db_if_not_exist()


if __name__ == "__main__":
    init()
