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


def _warm_up_webengine(app):
    """Start QtWebEngine before the main window is shown.

    Export previews are created lazily, but constructing the first QWebEngineView can
    start Chromium helper processes and briefly disrupt the visible application on
    Windows. Keeping one hidden view alive for the session moves that one-time startup
    cost before the main window becomes visible.
    """
    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtWebEngineWidgets import QWebEngineView

    warmup = QWebEngineView()
    warmup.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    warmup.resize(1, 1)
    warmup.load(QUrl("about:blank"))

    # Keep the view alive for the whole QApplication session so Chromium stays warm.
    app._webengine_warmup = warmup
    return warmup


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

    # Required for QWebEngineView (PNG export / live preview) on some platforms.
    # This must be set before QApplication is constructed.
    from PySide6.QtCore import Qt

    QtWidgets.QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    app = QtWidgets.QApplication(sys.argv)
    _warm_up_webengine(app)

    window = MainWindow()
    resources_rc.qInitResources()

    extra = {
        "font_family": "Roboto",
    }

    # Style the application before the first visible frame to avoid a second visual
    # transition during startup.
    apply_stylesheet(
        app,
        theme="dark_blue.xml",
        invert_secondary=False,
        extra=extra,
        css_file=os.path.join(utils.install_root(), "./theme/custom.css"),
    )

    window.show()
    _logger.info(f"Starting up... Install root: {utils.install_root()}")
    app.exec()


if __name__ == "__main__":
    pass
