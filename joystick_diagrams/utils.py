import logging
import os
import sys
from pathlib import Path

_logger = logging.getLogger(__name__)

JOYSTICK_DIAGRAMS_DATA_DIR = "Joystick Diagrams"


def data_root() -> Path:
    """Returns the user data path for storage of data"""

    root = (
        Path.joinpath(Path().home(), "AppData", "Roaming", JOYSTICK_DIAGRAMS_DATA_DIR)
        if sys.platform == "win32"
        else Path(
            os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        )
        / JOYSTICK_DIAGRAMS_DATA_DIR
    )

    if not root.exists():
        create_directory(root)

    return Path.joinpath(root)


def plugin_data_root() -> Path:
    """Returns the user data path for storage of plugin data"""

    root = Path.joinpath(data_root(), "plugins")
    if not root.is_dir():
        create_directory(root)
    return root


def create_directory(directory) -> None:
    try:
        if not Path(directory).exists():
            Path(directory).mkdir(parents=True)
    except PermissionError:
        _logger.error(
            f"Permission denied creating directory: {directory}. "
            f"Check folder permissions or run as administrator."
        )
        raise
    except OSError as error:
        _logger.error(f"Failed to create directory: {directory} with {error}")


def check_path_readable(path: Path) -> bool:
    """Check if a path is readable by the current user.

    Returns True if readable, raises PermissionError with a clear message if not.
    """
    try:
        if path.is_file():
            with open(path, "r"):
                pass
        elif path.is_dir():
            list(path.iterdir())
        return True
    except PermissionError as err:
        raise PermissionError(
            f"Permission denied reading '{path}'. "
            f"This may require administrator access or adjusted folder permissions."
        ) from err


def check_path_writable(path: Path) -> bool:
    """Check if a directory path is writable by the current user.

    Returns True if writable, raises PermissionError with a clear message if not.
    """
    try:
        test_dir = path if path.is_dir() else path.parent
        test_file = test_dir / ".jd_write_test"
        test_file.touch()
        test_file.unlink()
        return True
    except PermissionError as err:
        raise PermissionError(
            f"Permission denied writing to '{path}'. "
            f"Choose a different location or adjust folder permissions."
        ) from err
    except OSError as err:
        raise PermissionError(
            f"Cannot write to '{path}': {err}. "
            f"Choose a different location or adjust folder permissions."
        ) from err


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
