import logging
import sys

from PySide6 import QtWidgets
from qt_material import apply_stylesheet  # type: ignore

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db import db_init
from joystick_diagrams.plugin_manager import ParserPluginManager
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
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()

    extra = {
        "font_family": "Roboto",
    }

    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False, extra=extra)

    app.exec()


if __name__ == "__main__":
    pass
