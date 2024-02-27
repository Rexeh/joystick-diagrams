import logging
import os
import sys

from PySide6 import QtWidgets
from qt_material import apply_stylesheet

from joystick_diagrams import utils  # type: ignore
from joystick_diagrams.app_state import AppState
from joystick_diagrams.db import db_init
from joystick_diagrams.plugin_manager import ParserPluginManager
from joystick_diagrams.ui import resources_rc
from joystick_diagrams.ui.main_window import MainWindow

_logger = logging.getLogger(__name__)


def init():
    # Setup datastore
    db_init.init()
    # -------------------------------

    # -- Initialise Plugins System --
    plugins = ParserPluginManager()
    plugins.load_discovered_plugins()
    plugins.create_plugin_wrappers()

    # Setup global state with plugins
    _state = AppState(plugin_manager=plugins)
    # -------------------------------

    # Setup UI and begin thread
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR"] = "1"

    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    resources_rc.qInitResources()
    window.show()

    extra = {
        "font_family": "Roboto",
    }

    apply_stylesheet(
        app,
        theme="dark_blue.xml",
        invert_secondary=False,
        extra=extra,
        css_file=os.path.join(utils.install_root(), "./theme/custom.css"),
    )
    _logger.info(f"Starting up... Install root: {utils.install_root()}")
    app.exec()


if __name__ == "__main__":
    pass
