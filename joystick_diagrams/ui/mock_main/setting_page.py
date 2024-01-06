import logging
import sys
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets
from qt_material import apply_stylesheet

from joystick_diagrams.plugin_manager import ParserPluginManager
from joystick_diagrams.ui.mock_main import embed_UI
from joystick_diagrams.ui.mock_main.qt_designer import setting_page_ui


def initialise_plugins() -> ParserPluginManager | None:
    return ParserPluginManager() or None


_logger = logging.getLogger(__name__)
_plugins_list = initialise_plugins()
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)  # type: ignore
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)  # type: ignore


class settingPage(
    QtWidgets.QMainWindow, setting_page_ui.Ui_Form
):  # Refactor pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        # self.initalise_plugin_menu()
        # self.tab_2_content = embed_UI.EmbedWidget(self.tab_2)
        # self.pluginRemove.setProperty("class", "danger")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = settingPage()
    window.show()
    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False)
    app.exec()
