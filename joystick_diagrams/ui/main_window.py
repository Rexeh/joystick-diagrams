import logging
import os

import qtawesome as qta  # type:  ignore
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
)

from joystick_diagrams import version
from joystick_diagrams.app_state import AppState
from joystick_diagrams.ui import configure_page, export_page, setting_page
from joystick_diagrams.ui.qt_designer import main_window
from joystick_diagrams.utils import install_root

_logger = logging.getLogger(__name__)

JD_ICON = os.path.join(install_root(), r"img\logo.ico")


class MainWindow(
    QMainWindow, main_window.Ui_MainWindow
):  # Refactor pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()

        window_icon = QIcon(JD_ICON)
        self.setWindowIcon(window_icon)

        self.setupSectionButton.clicked.connect(self.load_setting_widget)
        self.customiseSectionButton.clicked.connect(self.load_other_widget)
        self.exportSectionButton.clicked.connect(self.load_export_page)
        self.window_content = None

        # Plugins Menu Controls
        self.setupSectionButton.setIcon(
            qta.icon("fa5s.cog", color="white", color_active="green")
        )
        self.setupSectionButton.setToolTip("Manage plugins")
        self.setupSectionButton.setIconSize(QSize(32, 32))

        # Customise Menu  Controls
        self.customiseSectionButton.setIcon(
            qta.icon("fa5s.tools", color="white", color_active="green")
        )
        self.customiseSectionButton.setIconSize(QSize(32, 32))
        self.customiseSectionButton.setToolTip(
            "Setup your profiles, and customise your binds"
        )

        # Export Menu Controls
        self.exportSectionButton.setIcon(
            qta.icon("fa5s.file-export", color="white", color_active="green")
        )
        self.exportSectionButton.setIconSize(QSize(32, 32))
        self.exportSectionButton.setToolTip("Export your profiles to diagrams")

        # Load default tab
        self.setupSectionButton.click()
        self.load_setting_widget()

        # Window Setup
        self.setWindowTitle(f"Joystick Diagrams - {version.get_current_version()}")

    def load_setting_widget(self):
        if self.window_content:
            self.window_content.hide()
        self.window_content = setting_page.PluginsPage()
        # self.window_content.setParent(self.horizontalLayout_2)
        self.horizontalLayout_2.addWidget(self.window_content)
        self.window_content.show()

    def load_other_widget(self):
        if self.window_content:
            self.window_content.hide()
        self.window_content = configure_page.configurePage()
        # self.window_content.setParent(self.horizontalLayout_2)
        self.horizontalLayout_2.addWidget(self.window_content)
        self.window_content.show()

    def load_export_page(self):
        if self.window_content:
            self.window_content.hide()
        self.window_content = export_page.ExportPage()
        # self.window_content.setParent(self.horizontalLayout_2)
        self.horizontalLayout_2.addWidget(self.window_content)
        self.window_content.show()


if __name__ == "__main__":
    pass
