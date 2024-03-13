"""Handles initialistion of DB for Joystick Diagrams.

Author: Robert Cox
"""

import logging

from joystick_diagrams import utils
from joystick_diagrams.db import (
    db_bind_text,
    db_device_management,
    db_plugin_data,
    db_profile_parents,
    db_profiles,
    db_settings,
)

_logger = logging.getLogger(__name__)


def init() -> None:
    _logger.info("Initialising datastores")

    utils.create_directory(utils.data_root().joinpath("data"))
    db_device_management.create_new_db_if_not_exist()
    db_bind_text.create_new_db_if_not_exist()
    db_plugin_data.create_new_db_if_not_exist()
    db_settings.create_new_db_if_not_exist()
    db_profiles.create_new_db_if_not_exist()
    db_profile_parents.create_new_db_if_not_exist()


if __name__ == "__main__":
    init()
