import logging
from pathlib import Path
from joystick_diagrams import version

_logger = logging.getLogger(__name__)


def create_directory(directory) -> None:  # pylint: disable=missing-function-docstring
    try:
        if not Path(directory).exists():
            Path(directory).mkdir()
    except OSError as error:
        _logger.error(f"Failed to create directory: {directory} with {error}")


def get_version() -> str:
    """
    Returns the current version of the application from Version File

    Returns: String
    """
    return "Version: " + version.VERSION
