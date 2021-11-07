from pathlib import Path
from joystick_diagrams import version
import logging

_logger = logging.getLogger(__name__)


def create_directory(directory):
    if not Path.exists(directory):
        return Path.mkdir(directory)
    else:
        _logger.error("Failed to create directory: {}".format(directory), "error")
        return False


def getVersion():
    return "Version: " + version.VERSION
