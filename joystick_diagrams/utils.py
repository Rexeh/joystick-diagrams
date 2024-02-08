import functools
import logging
from pathlib import Path

from joystick_diagrams.exceptions import JoystickDiagramsError

_logger = logging.getLogger(__name__)


def create_directory(directory) -> None:  # pylint: disable=missing-function-docstring
    try:
        if not Path(directory).exists():
            Path(directory).mkdir()
    except OSError as error:
        _logger.error(f"Failed to create directory: {directory} with {error}")


def handle_bare_exception(exception_type):
    """Handles bare exception by wrapping it in a Joystick Diagrams exception type.

    Default type is JoystickDiagramsException
    """

    if not exception_type:
        exception_type = JoystickDiagramsError

    def outer(func):
        @functools.wraps(func)
        def inner():
            try:
                return func()
            except Exception as e:
                raise exception_type(
                    f"An error occured from within the plugin. {e}"
                ) from e

        return inner

    return outer
