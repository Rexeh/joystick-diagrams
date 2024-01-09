import logging
import sys
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from qt_material import apply_stylesheet

from joystick_diagrams.app_state import appState
from joystick_diagrams.plugin_manager import ParserPluginManager
from joystick_diagrams.ui.mock_main import embed_UI, setting_page
from joystick_diagrams.ui.mock_main.qt_designer import main_window

_logger = logging.getLogger(__name__)

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)  # type: ignore
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)  # type: ignore


class MainWindow(
    QtWidgets.QMainWindow, main_window.Ui_MainWindow
):  # Refactor pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        # self.initalise_plugin_menu()
        # self.tab_2_content = embed_UI.EmbedWidget(self.tab_2)
        # self.pluginRemove.setProperty("class", "danger")
        self.appState = appState()

        self.setupSectionButton.clicked.connect(self.load_setting_widget)
        self.customiseSectionButton.clicked.connect(self.load_other_widget)
        self.window_content = None

    def load_setting_widget(self):
        if self.window_content:
            self.window_content.hide()
        self.window_content = setting_page.settingPage()
        self.window_content.setParent(self.activeMainWindowWidget)
        self.window_content.show()

    def load_other_widget(self):
        if self.window_content:
            self.window_content.hide()
        self.window_content = embed_UI.EmbedWidget()
        self.window_content.setParent(self.activeMainWindowWidget)
        self.window_content.show()


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
