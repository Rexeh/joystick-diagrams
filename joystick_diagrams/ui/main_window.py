import logging
import os

import qtawesome as qta
from PySide6.QtCore import QCoreApplication, QSize, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QToolButton,
    QWidget,
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
from joystick_diagrams.utils import data_root

_logger = logging.getLogger(__name__)


class MainWindow(QMainWindow, main_window.Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self._setup_menu_bar()

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
            qta.icon("fa5s.chevron-right", color="#515761").pixmap(QSize(14, 14))
        )
        self.chevron_1.setFixedSize(14, 14)
        self.chevron_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chevron_1.setProperty("class", "nav-chevron")

        self.chevron_2 = QLabel()
        self.chevron_2.setPixmap(
            qta.icon("fa5s.chevron-right", color="#515761").pixmap(QSize(14, 14))
        )
        self.chevron_2.setFixedSize(14, 14)
        self.chevron_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chevron_2.setProperty("class", "nav-chevron")

        # Insert chevrons between the buttons in topnav_layout
        # Layout order after setupUi: [Setup(0), Customise(1), Export(2)]
        # Insert at index 1 (between Setup and Customise) and index 3 (between Customise and Export)
        self.topnav_layout.insertWidget(
            1, self.chevron_1, 0, Qt.AlignmentFlag.AlignVCenter
        )
        self.topnav_layout.insertWidget(
            3, self.chevron_2, 0, Qt.AlignmentFlag.AlignVCenter
        )

        # Status Bar
        self.progressBar = QProgressBar()
        self.statusLabel = QLabel()
        self.statusLabel.setText("Waiting...")

        self.statusBar().addPermanentWidget(self.statusLabel, 1)
        self.statusBar().addPermanentWidget(self.progressBar, 1)

        # Nav bar setup
        self.topnav_layout.setSpacing(0)
        self.topnav_layout.setContentsMargins(0, 5, 0, 5)

        # Menu row uses topnav_additional_layout — see _setup_menu_bar

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

        # Settings — icon-only, secondary prominence
        self.settings_icon_default = qta.icon("fa5s.sliders-h", color="#9AA0A6")
        self.settings_icon_active = qta.icon("fa5s.sliders-h", color="white")
        self.settingsSectionButton = QPushButton(self.centralwidget)
        self.settingsSectionButton.setIcon(self.settings_icon_default)
        self.settingsSectionButton.setIconSize(QSize(24, 24))
        self.settingsSectionButton.setFixedSize(QSize(50, 50))
        self.settingsSectionButton.setToolTip("Settings")
        self.settingsSectionButton.setProperty("class", "nav-icon-button")
        self.settingsSectionButton.setCheckable(True)
        self.settingsSectionButton.clicked.connect(self.load_settings_page)
        self.topnav_layout.addWidget(
            self.settingsSectionButton, 0, Qt.AlignmentFlag.AlignVCenter
        )

        # Disable Additional Menu Controls

        self.additional_menus = [self.exportSectionButton, self.customiseSectionButton]
        self.disable_additional_menus()

        # Load default tab
        self.load_setting_widget()
        self.setupSectionButton.click()

        # Window Setup
        self.setWindowTitle(f"Joystick Diagrams - {version.get_current_version()}")

        self.check_for_new_version()

    def _setup_menu_bar(self):
        # The Qt-Designer QMenuBar is pinned to 21px and setCornerWidget is
        # unreliable across styles — hide it and use a custom row instead.
        self.menuBar().hide()

        row = self.topnav_additional_layout
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(4)

        # LEFT: Help popup
        help_btn = QToolButton()
        help_btn.setText("Help")
        help_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        help_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        help_btn.setAutoRaise(True)
        help_btn.setFixedHeight(26)
        help_btn.setObjectName("jdMenuHelp")
        help_btn.setMenu(self._build_help_menu(help_btn))
        row.addWidget(help_btn)

        row.addStretch(1)

        # RIGHT: external links
        def link(icon_name, icon_color, text, tooltip, handler, variant="link"):
            btn = QToolButton()
            btn.setIcon(qta.icon(icon_name, color=icon_color))
            btn.setIconSize(QSize(14, 14))
            btn.setText(text)
            btn.setToolTip(tooltip)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setAutoRaise(True)
            btn.setFixedHeight(26)
            btn.setObjectName("jdMenuLinkCta" if variant == "cta" else "jdMenuLink")
            btn.clicked.connect(handler)
            return btn

        row.addWidget(
            link(
                "fa5s.globe",
                "#9AA0A6",
                "Website",
                "joystick-diagrams.com",
                self._open_website,
            )
        )
        row.addWidget(
            link(
                "fa5b.github",
                "#9AA0A6",
                "GitHub",
                "View source on GitHub",
                self._open_github,
            )
        )
        row.addWidget(
            link(
                "fa5b.discord",
                "#9AA0A6",
                "Discord",
                "Join the Discord community",
                self._open_discord,
            )
        )
        row.addWidget(
            link(
                "fa5s.mug-hot",
                "#F59E0B",
                "Buy Me a Coffee",
                "Support development",
                self._open_buymeacoffee,
                variant="cta",
            )
        )

        # Thin divider under the row so it reads as a menu band
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("jdMenuDivider")
        divider.setFixedHeight(1)
        self.verticalLayout.insertWidget(1, divider)

    def _build_help_menu(self, parent: QWidget) -> QMenu:
        menu = QMenu(parent)

        support_action = QAction("Support", self)
        support_action.setToolTip("Get help on Discord")
        support_action.triggered.connect(self._open_discord)
        menu.addAction(support_action)

        menu.addSeparator()

        open_logs_action = QAction("Open Logs Folder", self)
        open_logs_action.triggered.connect(self._open_logs_folder)
        menu.addAction(open_logs_action)

        self._debug_action = QAction("Debug Mode", self)
        self._debug_action.setCheckable(True)
        self._debug_action.setChecked(False)
        self._debug_action.triggered.connect(self._toggle_debug_mode)
        menu.addAction(self._debug_action)

        menu.addSeparator()

        check_updates_action = QAction("Check for Updates", self)
        check_updates_action.triggered.connect(self._check_for_updates)
        menu.addAction(check_updates_action)

        about_action = QAction("About Joystick Diagrams", self)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        return menu

    def _open_discord(self):
        QDesktopServices.openUrl("https://discord.gg/UUyRUuX2dX")

    def _open_website(self):
        QDesktopServices.openUrl("https://joystick-diagrams.com")

    def _open_github(self):
        QDesktopServices.openUrl("https://github.com/Rexeh/joystick-diagrams")

    def _open_buymeacoffee(self):
        QDesktopServices.openUrl(
            "https://www.paypal.com/cgi-bin/webscr"
            "?cmd=_s-xclick&hosted_button_id=WLLDYGQM5Z39W&source=url"
        )

    def _open_logs_folder(self):
        log_path = data_root() / "logs"
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_path)))

    def _toggle_debug_mode(self, checked):
        if checked:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)

    def _check_for_updates(self):
        version_check = version.perform_version_check()
        if version_check is False:
            self.statusLabel.setText(
                "An update is available! Visit joystick-diagrams.com"
            )
        elif version_check is True:
            self.statusLabel.setText("You're up to date")
        else:
            self.statusLabel.setText("Unable to check for updates")

    def _show_about(self):
        QMessageBox.about(
            self,
            "About Joystick Diagrams",
            f"Joystick Diagrams v{version.get_current_version()}\n\n"
            "Create diagrams for your joystick and HOTAS setups.",
        )

    def check_for_new_version(self):
        _logger.info("Checking version...")
        self._check_for_updates()

    def set_style(self):
        stylesheet = self.app.styleSheet()
        theme_path = os.path.join(os.getcwd(), "joystick_diagrams/theme/custom.css")

        with open(theme_path) as file:
            self.app.setStyleSheet(stylesheet + file.read().format(**os.environ))

    def disable_additional_menus(self):
        for x in self.additional_menus:
            x.setDisabled(True)
            x.setToolTip("Run plugins in Setup first to unlock")
        # Reset chevrons to default gray
        self.chevron_1.setPixmap(
            qta.icon("fa5s.chevron-right", color="#515761").pixmap(QSize(14, 14))
        )
        self.chevron_2.setPixmap(
            qta.icon("fa5s.chevron-right", color="#515761").pixmap(QSize(14, 14))
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
