import os
import sys

if getattr(sys, "frozen", False):
    from pathlib import Path as _Path

    _lib = _Path(sys.executable).parent / "lib"
    _pyside6 = _lib / "PySide6"

    for _dll_dir in (_lib, _pyside6):
        if _dll_dir.is_dir():
            os.add_dll_directory(str(_dll_dir))

    _plugins = _pyside6 / "plugins"
    if _plugins.is_dir():
        os.environ.setdefault("QT_PLUGIN_PATH", str(_plugins))

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from joystick_diagrams import app_init
from joystick_diagrams.utils import create_directory, data_root

log_path = Path.joinpath(data_root(), "logs")
create_directory(str(log_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(module)s %(filename)s - %(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            str(Path.joinpath(log_path, "application.log")),
            mode="a",
            maxBytes=5 * 1000000,
            backupCount=1,
        ),
    ],
)
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

if __name__ == "__main__":
    try:
        app_init.init()

    except Exception as error:
        _logger.exception(error)
