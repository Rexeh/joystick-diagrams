import logging
import os

import qtawesome as qta  # type:  ignore
from PySide6.QtCore import QCoreApplication, QSize, Qt
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
)

from joystick_diagrams import version
from joystick_diagrams.app_state import AppState
from joystick_diagrams.ui import (
    configure_page,
    export_page,
    plugins_page,
    settings_page,
    ui_consts,
)
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

        # Page stack — pages are created lazily and cached
        self._page_stack = QStackedWidget()
        self.main_content_layout.addWidget(self._page_stack)
        self._setup_page = None
        self._customise_page = None
        self._export_page = None
        self._settings_page = None

        # Step numbers on workflow buttons
        self.setupSectionButton.setText("1. Setup")
        self.customiseSectionButton.setText("2. Customise")
        self.exportSectionButton.setText("3. Export")

        # Chevron connectors between workflow buttons
        self.chevron_1 = QLabel()
        self.chevron_1.setPixmap(
            qta.icon("fa5s.chevron-right", color="#3C4043").pixmap(QSize(14, 14))
        )
        self.chevron_1.setFixedSize(14, 14)
        self.chevron_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chevron_1.setProperty("class", "nav-chevron")

        self.chevron_2 = QLabel()
        self.chevron_2.setPixmap(
            qta.icon("fa5s.chevron-right", color="#3C4043").pixmap(QSize(14, 14))
        )
        self.chevron_2.setFixedSize(14, 14)
        self.chevron_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chevron_2.setProperty("class", "nav-chevron")

        # Insert chevrons between the buttons in topnav_layout
        # Layout order after setupUi: [Setup(0), Customise(1), Export(2)]
        # Insert at index 1 (between Setup and Customise) and index 3 (between Customise and Export)
        self.topnav_layout.insertWidget(1, self.chevron_1)
        self.topnav_layout.insertWidget(3, self.chevron_2)

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

        nav_icon_size = QSize(24, 24)

        self.setup_icon_default = qta.icon("fa5s.cog", color="#9AA0A6")
        self.setup_icon_active = qta.icon("fa5s.cog", color="white")
        self.setupSectionButton.setIcon(self.setup_icon_default)
        self.setupSectionButton.setToolTip("Manage plugins")
        self.setupSectionButton.setIconSize(nav_icon_size)
        self.setupSectionButton.setProperty("class", "nav-button left")
        self.setupSectionButton.setCheckable(True)

        # Customise Menu Controls
        self.customise_icon_default = qta.icon("fa5s.tools", color="#9AA0A6")
        self.customise_icon_active = qta.icon("fa5s.tools", color="white")
        self.customiseSectionButton.setIcon(self.customise_icon_default)
        self.customiseSectionButton.setIconSize(nav_icon_size)
        self.customiseSectionButton.setToolTip(
            "Setup your profiles, and customise your binds"
        )
        self.customiseSectionButton.setProperty("class", "nav-button middle")
        self.customiseSectionButton.setCheckable(True)

        # Export Menu Controls
        self.export_icon_default = qta.icon("fa5s.file-export", color="#9AA0A6")
        self.export_icon_active = qta.icon("fa5s.file-export", color="white")
        self.exportSectionButton.setIcon(self.export_icon_default)
        self.exportSectionButton.setIconSize(nav_icon_size)
        self.exportSectionButton.setToolTip("Export your profiles to diagrams")
        self.exportSectionButton.setProperty("class", "nav-button right")
        self.exportSectionButton.setCheckable(True)

        # Spacer to separate workflow buttons from settings
        self.topnav_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        # Settings - visually separated from the workflow flow
        self.settings_icon_default = qta.icon("fa5s.sliders-h", color="#9AA0A6")
        self.settings_icon_active = qta.icon("fa5s.sliders-h", color="white")
        self.settingsSectionButton = QPushButton(self.centralwidget)
        self.settingsSectionButton.setText("Settings")
        self.settingsSectionButton.setIcon(self.settings_icon_default)
        self.settingsSectionButton.setIconSize(nav_icon_size)
        self.settingsSectionButton.setToolTip("Application settings")
        self.settingsSectionButton.setProperty("class", "nav-button standalone")
        self.settingsSectionButton.setCheckable(True)
        self.settingsSectionButton.clicked.connect(self.load_settings_page)
        self.topnav_layout.addWidget(self.settingsSectionButton)

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
        for x in self.additional_menus:
            x.setDisabled(True)
            x.setToolTip("Run plugins in Setup first to unlock")
        # Reset chevrons to default gray
        self.chevron_1.setPixmap(
            qta.icon("fa5s.chevron-right", color="#3C4043").pixmap(QSize(14, 14))
        )
        self.chevron_2.setPixmap(
            qta.icon("fa5s.chevron-right", color="#3C4043").pixmap(QSize(14, 14))
        )

    def enable_additional_menus(self):
        for x in self.additional_menus:
            x.setDisabled(False)
            x.setToolTip("")
        # Light up chevrons to show workflow progression
        self.chevron_1.setPixmap(
            qta.icon("fa5s.chevron-right", color="#34D399").pixmap(QSize(14, 14))
        )
        self.chevron_2.setPixmap(
            qta.icon("fa5s.chevron-right", color="#34D399").pixmap(QSize(14, 14))
        )

    def update_menus_from_profile_count(self, data: int):
        self._invalidate_data_pages()
        self.enable_additional_menus() if data > 0 else self.disable_additional_menus()

    def _update_nav_icons(self, active: str):
        """Update nav button icons to show white when active, gray when inactive."""
        self.setupSectionButton.setIcon(
            self.setup_icon_active if active == "setup" else self.setup_icon_default
        )
        self.customiseSectionButton.setIcon(
            self.customise_icon_active
            if active == "customise"
            else self.customise_icon_default
        )
        self.exportSectionButton.setIcon(
            self.export_icon_active if active == "export" else self.export_icon_default
        )
        self.settingsSectionButton.setIcon(
            self.settings_icon_active
            if active == "settings"
            else self.settings_icon_default
        )

    def load_setting_widget(self):
        self.settingsSectionButton.setChecked(False)
        self.setupSectionButton.setChecked(True)
        self._update_nav_icons("setup")

        if self._setup_page is None:
            self._setup_page = plugins_page.PluginsPage()
            self._setup_page.total_parsed_profiles.connect(
                self.update_menus_from_profile_count
            )
            self._page_stack.addWidget(self._setup_page)
        else:
            self._setup_page.refresh()

        self._page_stack.setCurrentWidget(self._setup_page)

    def load_customise_page(self):
        self.settingsSectionButton.setChecked(False)
        self.customiseSectionButton.setChecked(True)
        self._update_nav_icons("customise")

        if self._customise_page is None:
            self._customise_page = configure_page.configurePage()
            self._page_stack.addWidget(self._customise_page)

        self._page_stack.setCurrentWidget(self._customise_page)

    def load_export_page(self):
        self.settingsSectionButton.setChecked(False)
        self.exportSectionButton.setChecked(True)
        self._update_nav_icons("export")

        if self._export_page is None:
            self._export_page = export_page.ExportPage()
            self._page_stack.addWidget(self._export_page)
        else:
            self._export_page.refresh()

        self._page_stack.setCurrentWidget(self._export_page)

    def _uncheck_workflow_buttons(self):
        """Uncheck the Setup/Customise/Export button group."""
        self.buttonGroup_2.setExclusive(False)
        for button in self.buttonGroup_2.buttons():
            button.setChecked(False)
        self.buttonGroup_2.setExclusive(True)

    def load_settings_page(self):
        self._uncheck_workflow_buttons()
        self.settingsSectionButton.setChecked(True)
        self._update_nav_icons("settings")

        if self._settings_page is None:
            self._settings_page = settings_page.SettingsPage()
            self._page_stack.addWidget(self._settings_page)
        else:
            self._settings_page.refresh()

        self._page_stack.setCurrentWidget(self._settings_page)

    def _invalidate_data_pages(self):
        """Destroy cached Customise/Export pages so they refresh on next visit."""
        for attr in ("_customise_page", "_export_page"):
            page = getattr(self, attr)
            if page is not None:
                self._page_stack.removeWidget(page)
                page.deleteLater()
                setattr(self, attr, None)


if __name__ == "__main__":
    pass
