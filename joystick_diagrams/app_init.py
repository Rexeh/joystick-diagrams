import logging
import os
import sys

from PySide6 import QtWidgets
from qt_material import apply_stylesheet

from joystick_diagrams import utils
from joystick_diagrams.app_state import AppState
from joystick_diagrams.db import db_handler
from joystick_diagrams.plugins.output_plugin_manager import OutputPluginManager
from joystick_diagrams.plugins.plugin_manager import ParserPluginManager
from joystick_diagrams.ui import resources_rc
from joystick_diagrams.ui.main_window import MainWindow

_logger = logging.getLogger(__name__)


def init():
    # Setup datastore
    db_handler.init()
    # -------------------------------

    # -- Initialise Plugins System --
    plugins = ParserPluginManager()
    plugins.load_discovered_plugins()
    plugins.create_plugin_wrappers()

    output_plugins = OutputPluginManager()
    output_plugins.load_discovered_plugins()
    output_plugins.create_plugin_wrappers()

    # Setup global state with plugins
    _state = AppState(plugin_manager=plugins, output_plugin_manager=output_plugins)
    # -------------------------------

    # Setup UI and begin thread
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR"] = "1"

    # Required for QWebEngineView (PNG export) on some platforms
    from PySide6.QtCore import Qt

    QtWidgets.QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    # jdeditor:// (layout editor canvas, previews) must exist before the app object
    from joystick_diagrams.ui.layout_editor.scheme import register_scheme

    register_scheme()

    # Qt's own warnings go to the log; harmless thumbnail noise only at debug level
    from joystick_diagrams.qt_messages import install_qt_message_filter

    install_qt_message_filter()

    app = QtWidgets.QApplication(sys.argv)

    resources_rc.qInitResources()
    extra = {
        "font_family": "Roboto",
    }

    # Styled before the first show: the four-stage shell starts reading the games
    # in the background right after it appears (MainWindow.showEvent).
    apply_stylesheet(
        app,
        theme="dark_blue.xml",
        invert_secondary=False,
        extra=extra,
        css_file=os.path.join(utils.install_root(), "./theme/custom.css"),
    )

    window = MainWindow()
    window.show()
    _logger.info(f"Starting up... Install root: {utils.install_root()}")
    app.exec()


if __name__ == "__main__":
    pass
