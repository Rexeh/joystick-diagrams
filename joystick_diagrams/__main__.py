import logging
import sys
from pathlib import Path

from PySide6 import QtWidgets
from qt_material import apply_stylesheet

from joystick_diagrams import app_init
from joystick_diagrams.config import settings
from joystick_diagrams.plugin_manager import ParserPluginManager

# from joystick_diagrams.ui.main_window.main_window import MainWindow
from joystick_diagrams.ui.mock_main.mock_main import MainWindow

_logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Setup basic logging

    Args:
    ----
      loglevel (int): minimum loglevel for emitting messages
    """
    log_dir = Path("logs")
    log_file = Path("app.log")
    log_file_location = Path.joinpath(log_dir, log_file)

    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"

    if not Path.exists(log_dir):
        Path.mkdir(log_dir)

    logging.basicConfig(
        level=get_log_level(),
        filename=log_file_location,
        format=logformat,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def initialise_plugins() -> ParserPluginManager:
    return ParserPluginManager()


def initialise_ui() -> None:
    pass


def get_log_level() -> int:
    try:
        return logging.getLevelNamesMapping()[settings.logLevel]
    except KeyError:
        return logging.getLevelNamesMapping()["INFO"]


if __name__ == "__main__":
    setup_logging()
    try:
        # Initiate pre-loading
        app_init

        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.show()

        # Device Manager
        # _device_manager = threading.Thread(target=device_manager.run, daemon=True)
        # _device_manager.start()

        apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False)

        app.exec()
    except Exception as error:  # pylint: disable=broad-except
        _logger.exception(error)
