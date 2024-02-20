import functools
import logging
import os
import sys
from pathlib import Path

from joystick_diagrams.exceptions import JoystickDiagramsError

_logger = logging.getLogger(__name__)


def create_directory(directory) -> None:  # pylint: disable=missing-function-docstring
    try:
        if not Path(directory).exists():
            Path(directory).mkdir()
    except OSError as error:
        _logger.error(f"Failed to create directory: {directory} with {error}")


def install_root() -> str:  # pylint: disable=missing-function-docstring
    """Returns the currently root directory of the package

    "" in local development environments
    "path_to_frozen_app_exe" in frozen environment

    """
    return (
        os.path.dirname(sys.executable)
        if getattr(sys, "frozen", False)
        else os.path.dirname(__package__)
    )


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
