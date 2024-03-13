import logging
import os
import sys
from pathlib import Path

_logger = logging.getLogger(__name__)

JOYSTICK_DIAGRAMS_DATA_DIR = "Joystick Diagrams"


def data_root() -> Path:
    """Returns the user data path for storage of data"""
    return Path.joinpath(
        Path().home(), "AppData", "Roaming", JOYSTICK_DIAGRAMS_DATA_DIR
    )


def create_directory(directory) -> None:
    try:
        if not Path(directory).exists():
            Path(directory).mkdir()
    except OSError as error:
        _logger.error(f"Failed to create directory: {directory} with {error}")


def install_root() -> str:
    """Returns the current root directory of the package i.e. installation location

    "" in local development environments
    "path_to_frozen_app_exe" in frozen environment

    """
    return (
        os.path.dirname(sys.executable)
        if getattr(sys, "frozen", False)
        else os.path.dirname(__package__)
    )
