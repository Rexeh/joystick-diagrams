import logging
import os

import qtawesome as qta  # type:  ignore
from PySide6.QtCore import QCoreApplication, QSize
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
)

from joystick_diagrams import version
from joystick_diagrams.app_state import AppState
from joystick_diagrams.ui import configure_page, export_page, plugins_page, ui_consts
from joystick_diagrams.ui.qt_designer import main_window

_logger = logging.getLogger(__name__)


class MainWindow(QMainWindow, main_window.Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.app = QCoreApplication.instance()

        self.appState = AppState()

        self.appState.main_window = self

        window_icon = QIcon(ui_consts.JD_ICON)
        self.setWindowIcon(window_icon)

        self.setupSectionButton.clicked.connect(self.load_setting_widget)
        self.customiseSectionButton.clicked.connect(self.load_customise_page)
        self.exportSectionButton.clicked.connect(self.load_export_page)
        self.window_content = None

        # Menu Bars

        ## Menu Icons - Defined in instance as QTAwesome requires QApplication
        discord_icon = qta.icon("fa5b.discord", color="white", color_active="green")

        self.progressBar = QProgressBar()
        self.statusLabel = QLabel()
        self.statusLabel.setText("Waiting...")

        self.debug_mode = QCheckBox()
        self.debug_mode.setText("Debug")
        self.debug_mode.setChecked(False)
        self.debug_mode.stateChanged.connect(self.handle_debug_mode_switch)

        self.statusBar().addPermanentWidget(self.debug_mode)
        self.statusBar().addPermanentWidget(self.statusLabel, 1)
        self.statusBar().addPermanentWidget(self.progressBar, 1)

        # Top Additional Nav Setup

        self.topnav_layout.setSpacing(0)
        self.topnav_layout.setContentsMargins(0, 5, 0, 5)

        self.discord_pill = QPushButton()
        self.discord_pill.setText("Discord")
        self.discord_pill.setIcon(discord_icon)
        self.discord_pill.setProperty("class", "pill-button discord")

        self.website_pill = QPushButton()
        self.website_pill.setText("Website")
        self.website_pill.setIcon(QIcon(ui_consts.JD_ICON))
        self.website_pill.setProperty("class", "pill-button web")

        self.update_pill = QPushButton()
        self.update_pill.setText("An update is available!")
        self.update_pill.setHidden(True)
        self.update_pill.setIcon(QIcon(ui_consts.JD_ICON))
        self.update_pill.setProperty("class", "pill-button update")

        self.discord_pill.clicked.connect(self.open_discord_link)
        self.website_pill.clicked.connect(self.open_website_link)
        self.update_pill.clicked.connect(self.open_website_link)

        self.topnav_additional_layout.addStretch(1)

        # Top Nav Dev Refresh Button
        # self.styleButton = QPushButton("Refresh Style")
        # self.styleButton.clicked.connect(self.set_style)

        # self.styleTimer = QTimer()
        # self.styleTimer.setInterval(10000)
        # self.styleTimer.timeout.connect(self.set_style)
        # self.styleTimer.start()

        # self.topnav_additional_layout.addWidget(self.styleButton)
        self.topnav_additional_layout.addWidget(self.update_pill)
        self.topnav_additional_layout.addWidget(self.discord_pill)
        self.topnav_additional_layout.addWidget(self.website_pill)

        # Plugins Menu Controls

        # TODO move this out into styles

        self.setupSectionButton.setIcon(
            qta.icon("fa5s.cog", color="black", color_active="white")
        )
        self.setupSectionButton.setToolTip("Manage plugins")
        self.setupSectionButton.setIconSize(QSize(32, 32))
        self.setupSectionButton.setProperty("class", "nav-button left")

        self.setupSectionButton.setCheckable(True)

        # Customise Menu  Controls
        self.customiseSectionButton.setIcon(
            qta.icon("fa5s.tools", color="black", color_active="white")
        )
        self.customiseSectionButton.setIconSize(QSize(32, 32))
        self.customiseSectionButton.setToolTip(
            "Setup your profiles, and customise your binds"
        )
        self.customiseSectionButton.setProperty("class", "nav-button middle")
        self.customiseSectionButton.setCheckable(True)

        # Export Menu Controls
        self.exportSectionButton.setIcon(
            qta.icon("fa5s.file-export", color="black", color_active="white")
        )
        self.exportSectionButton.setIconSize(QSize(32, 32))
        self.exportSectionButton.setToolTip("Export your profiles to diagrams")
        self.exportSectionButton.setProperty("class", "nav-button right")
        self.exportSectionButton.setCheckable(True)

        # Disable Additional Menu Controls

        self.additional_menus = [self.exportSectionButton, self.customiseSectionButton]
        self.disable_additional_menus()

        # Load default tab
        self.load_setting_widget()
        self.setupSectionButton.click()

        # Window Setup
        self.setWindowTitle(f"Joystick Diagrams - {version.get_current_version()}")

        self.check_for_new_version()

    def check_for_new_version(self):
        _logger.info("Checking version...")
        version_check = version.perform_version_check()
        _logger.info(f"Version check was {version_check}")

        if version_check is False:
            self.update_pill.setHidden(False)

    def handle_debug_mode_switch(self, state):
        if state == 2:
            _logger.root.setLevel(logging.DEBUG)
        else:
            _logger.root.setLevel(logging.INFO)

    def set_style(self):
        stylesheet = self.app.styleSheet()
        theme_path = os.path.join(os.getcwd(), "joystick_diagrams/theme/custom.css")

        with open(theme_path) as file:
            self.app.setStyleSheet(stylesheet + file.read().format(**os.environ))

    def open_discord_link(self):
        QDesktopServices.openUrl("https://discord.gg/UUyRUuX2dX")

    def open_website_link(self):
        QDesktopServices.openUrl("https://joystick-diagrams.com")

    def disable_additional_menus(self):
        [x.setDisabled(True) for x in self.additional_menus]

    def enable_additional_menus(self):
        [x.setDisabled(False) for x in self.additional_menus]

    def update_menus_from_profile_count(self, data: int):
        self.enable_additional_menus() if data > 0 else self.disable_additional_menus()

    def load_setting_widget(self):
        self.setupSectionButton.setChecked(True)

        if self.window_content:
            self.window_content.hide()
        self.window_content = plugins_page.PluginsPage()
        self.window_content.total_parsed_profiles.connect(
            self.update_menus_from_profile_count
        )
        self.main_content_layout.addWidget(self.window_content)
        self.window_content.show()

    def load_customise_page(self):
        self.customiseSectionButton.setChecked(True)
        if self.window_content:
            self.window_content.hide()
        self.window_content = configure_page.configurePage()
        self.main_content_layout.addWidget(self.window_content)
        self.window_content.show()

    def load_export_page(self):
        self.exportSectionButton.setChecked(True)
        if self.window_content:
            self.window_content.hide()
        self.window_content = export_page.ExportPage()
        self.main_content_layout.addWidget(self.window_content)
        self.window_content.show()


if __name__ == "__main__":
    pass
