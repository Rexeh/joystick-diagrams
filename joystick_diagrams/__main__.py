import logging
import os
import sys
import threading
from pathlib import Path

from PyQt5 import QtWidgets
from qt_material import apply_stylesheet

from joystick_diagrams.adaptors.dcs.dcs_world import DCSWorldParser
from joystick_diagrams.adaptors.joystick_gremlin.joystick_gremlin import JoystickGremlin
from joystick_diagrams.adaptors.star_citizen.star_citizen import StarCitizen
from joystick_diagrams.classes import export
from joystick_diagrams.classes.version import version
from joystick_diagrams.config import settings
from joystick_diagrams.devices import device_manager
from joystick_diagrams.plugin_manager import ParserPluginManager
from joystick_diagrams.ui.main_window.main_window import MainWindow

_logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """

    log_dir = Path("logs")
    log_file = Path("jv.log")
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


def get_log_level():
    try:
        return logging.getLevelNamesMapping()[settings.logLevel]
    except KeyError:
        return logging.getLevelNamesMapping()["INFO"]


if __name__ == "__main__":
    setup_logging()
    try:
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.show()

        # Load Plugins
        plugins = initialise_plugins()

        # Device Manager
        # _device_manager = threading.Thread(target=device_manager.run, daemon=True)
        # _device_manager.start()

        apply_stylesheet(app, theme="dark_lightgreen.xml")

        app.exec()
    except Exception as error:  # pylint: disable=broad-except
        _logger.exception(error)
