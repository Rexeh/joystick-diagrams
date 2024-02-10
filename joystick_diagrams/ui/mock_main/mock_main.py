import logging
import sys

import qtawesome as qta
from PySide6 import QtWidgets
from PySide6.QtCore import QSize
from qt_material import apply_stylesheet

from joystick_diagrams import version
from joystick_diagrams.app_state import AppState
from joystick_diagrams.ui.mock_main import configure_page, export_page, setting_page
from joystick_diagrams.ui.mock_main.qt_designer import main_window

_logger = logging.getLogger(__name__)


class MainWindow(
    QtWidgets.QMainWindow, main_window.Ui_MainWindow
):  # Refactor pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()

        self.setupSectionButton.clicked.connect(self.load_setting_widget)
        self.customiseSectionButton.clicked.connect(self.load_other_widget)
        self.exportSectionButton.clicked.connect(self.load_export_page)
        self.window_content = None

        # verticalPolicy = QSizePolicy()
        # verticalPolicy.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        # self.setupSectionButton.setSizePolicy(verticalPolicy)
        self.setupSectionButton.setIcon(
            qta.icon(
                "fa5s.cog",
                color="white",
            )
        )
        self.setupSectionButton.setIconSize(QSize(32, 32))
        self.exportSectionButton.setIcon(
            qta.icon(
                "fa5s.file-export",
                color="white",
            )
        )
        self.exportSectionButton.setIconSize(QSize(32, 32))

        self.customiseSectionButton.setIcon(
            qta.icon(
                "fa5s.tools",
                color="white",
            )
        )
        self.customiseSectionButton.setIconSize(QSize(32, 32))
        # Load default tab
        self.load_setting_widget()

        # Window Setup
        self.setWindowTitle(f"Joystick Diagrams - {version.get_current_version()}")

    def load_setting_widget(self):
        if self.window_content:
            self.window_content.hide()
        self.window_content = setting_page.PluginsPage()
        self.window_content.setParent(self.activeMainWindowWidget)
        self.window_content.show()

    def load_other_widget(self):
        if self.window_content:
            self.window_content.hide()
        self.window_content = configure_page.configurePage()
        self.window_content.setParent(self.activeMainWindowWidget)
        self.window_content.show()

    def load_export_page(self):
        if self.window_content:
            self.window_content.hide()
        self.window_content = export_page.ExportPage()
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

    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False, extra=extra)
    app.exec()
