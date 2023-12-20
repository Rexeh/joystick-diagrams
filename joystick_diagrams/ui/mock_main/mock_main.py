import logging
import sys
from pathlib import Path

import PyQt5.QtQuick
import PyQt5.QtQuick.Controls
import PyQt5.QtQuick.Controls.Material
from PyQt5 import QtCore, QtGui, QtWidgets
from qt_material import apply_stylesheet

from joystick_diagrams.plugin_manager import ParserPluginManager
from joystick_diagrams.ui.mock_main import embed_UI
from joystick_diagrams.ui.mock_main.qt_designer import mock_UI


def initialise_plugins() -> ParserPluginManager | None:
    return ParserPluginManager() or None


_logger = logging.getLogger(__name__)
_plugins_list = initialise_plugins()
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)  # type: ignore
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)  # type: ignore


def initialise_ui() -> None:
    pass


def get_log_level():
    try:
        return logging.getLevelNamesMapping()[config.debugLevel]
    except KeyError:
        return logging.getLevelNamesMapping()["INFO"]


class MainWindow(QtWidgets.QMainWindow, mock_UI.Ui_MainWindow):  # Refactor pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        # self.initalise_plugin_menu()

        self.tab_2_content = embed_UI.EmbedWidget(self.tab_2)

        self.pushButton.setProperty("class", "danger")

    def initalise_plugin_menu(self):
        for plugin in _plugins_list.loaded_plugins:
            self.pushButton = QtWidgets.QPushButton(self.verticalLayoutWidget)
            self.pushButton.setFlat(False)
            self.pushButton.setObjectName(plugin.name)
            self.pushButton.setText(plugin.name)
            self.pushButton.setIcon(QtGui.QIcon(plugin.icon))
            self.pluginListContainer.addWidget(self.pushButton)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # ['dark_amber.xml',
    # 'dark_blue.xml',
    # 'dark_cyan.xml',
    # 'dark_lightgreen.xml',
    # 'dark_pink.xml',
    # 'dark_purple.xml',
    # 'dark_red.xml',
    # 'dark_teal.xml',
    # 'dark_yellow.xml',
    # 'light_amber.xml',
    # 'light_blue.xml',
    # 'light_cyan.xml',
    # 'light_cyan_500.xml',
    # 'light_lightgreen.xml',
    # 'light_pink.xml',
    # 'light_purple.xml',
    # 'light_red.xml',
    # 'light_teal.xml',
    # 'light_yellow.xml']

    extra = {
        # Button colors
        "danger": "#dc3545",
        "warning": "#ffc107",
        "success": "#17a2b8",
        # Font
        "font_family": "Windings",
    }

    css_override = open((Path(__file__).parent).joinpath("./custom.css"), "r").read()

    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False, extra=extra, css_file=css_override)
    app.exec()
