import logging
from pathlib import Path

_logger = logging.getLogger(__name__)


def create_directory(directory) -> None:  # pylint: disable=missing-function-docstring
    try:
        if not Path(directory).exists():
            Path(directory).mkdir()
    except OSError as error:
        _logger.error(f"Failed to create directory: {directory} with {error}")
