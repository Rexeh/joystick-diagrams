import logging
import shutil
import webbrowser
from datetime import datetime
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams import utils
from joystick_diagrams.app_state import AppState
from joystick_diagrams.conflict_strategy import (
    ALIAS_CONFLICT_STRATEGY_KEY,
    INHERITANCE_CONFLICT_STRATEGY_KEY,
    AliasConflictStrategy,
    InheritanceConflictStrategy,
    get_alias_strategy,
    get_inheritance_strategy,
)
from joystick_diagrams.db.db_settings import add_update_setting_value, get_setting
from joystick_diagrams.ui.widgets.section_header import SectionHeader

_logger = logging.getLogger(__name__)

OPEN_AFTER_EXPORT_SETTING_KEY = "open_after_export"
DATE_FORMAT_SETTING_KEY = "export_date_format"
DEFAULT_DATE_FORMAT = "%d/%m/%Y"

DATE_FORMAT_OPTIONS = [
    ("%d/%m/%Y", "DD/MM/YYYY"),
    ("%m/%d/%Y", "MM/DD/YYYY"),
    ("%Y-%m-%d", "YYYY-MM-DD"),
    ("%d-%m-%Y", "DD-MM-YYYY"),
    ("%d %b %Y", "DD Mon YYYY"),
    ("%B %d, %Y", "Month DD, YYYY"),
    ("%Y/%m/%d", "YYYY/MM/DD"),
]

ALIAS_STRATEGY_OPTIONS = [
    (AliasConflictStrategy.CONCATENATE, "Concatenate (combine into primary)"),
    (AliasConflictStrategy.MODIFIER, "Modifier (losing binding becomes a modifier)"),
]

INHERITANCE_STRATEGY_OPTIONS = [
    (
        InheritanceConflictStrategy.KEEP_EXISTING,
        "Keep existing (main profile wins)",
    ),
    (
        InheritanceConflictStrategy.CONCATENATE,
        "Concatenate (combine into primary)",
    ),
    (
        InheritanceConflictStrategy.MODIFIER,
        "Modifier (inherited binding becomes a modifier)",
    ),
]


class SettingsPage(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.appState = AppState()

        container = QWidget()
        root_layout = QHBoxLayout(container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(container)

        # Left sidebar navigation
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.setProperty("class", "settings-nav")

        nav_items = [
            ("fa5s.cog", "General"),
            ("fa5s.puzzle-piece", "Parser Plugins"),
            ("fa5s.plug", "Output Plugins"),
        ]
        for icon_name, label in nav_items:
            item = QListWidgetItem(qta.icon(icon_name, color="#9AA0A6"), label)
            item.setSizeHint(QSize(0, 44))
            self.nav_list.addItem(item)

        root_layout.addWidget(self.nav_list)

        # Right content area
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_general_tab())
        self.stack.addWidget(self._create_parser_plugins_tab())
        self.stack.addWidget(self._create_output_plugins_tab())
        root_layout.addWidget(self.stack, 1)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

    def refresh(self):
        """Refresh data-dependent tabs when returning to this page."""
        self._populate_parser_plugin_cards()
        self._populate_output_plugin_cards()

    # ── General Tab ──

    def _create_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = SectionHeader("fa5s.cog", "General Settings")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(0, 4, 0, 0)

        date_row = QHBoxLayout()
        date_row.setSpacing(12)

        self.date_format_combo = QComboBox()
        self.date_format_combo.setProperty("class", "view-binds-list")
        self.date_format_combo.setMinimumWidth(220)

        now = datetime.now()
        current_format = get_setting(DATE_FORMAT_SETTING_KEY) or DEFAULT_DATE_FORMAT
        selected_index = 0

        for i, (fmt, label) in enumerate(DATE_FORMAT_OPTIONS):
            preview = now.strftime(fmt)
            self.date_format_combo.addItem(f"{label}  ({preview})", fmt)
            if fmt == current_format:
                selected_index = i

        self.date_format_combo.setCurrentIndex(selected_index)
        self.date_format_combo.currentIndexChanged.connect(self._on_date_format_changed)

        date_row.addWidget(self.date_format_combo)
        date_row.addStretch(1)

        date_label = QLabel("Export date format")
        date_label.setObjectName("device_help_label")
        form.addRow(date_label, date_row)

        # Open export folder toggle
        self.open_after_export_cb = QCheckBox("Open export folder after export")
        saved_open = get_setting(OPEN_AFTER_EXPORT_SETTING_KEY)
        self.open_after_export_cb.setChecked(saved_open != "false")  # default True
        self.open_after_export_cb.stateChanged.connect(
            self._on_open_after_export_changed
        )
        form.addRow("", self.open_after_export_cb)

        # Alias merge strategy
        self.alias_strategy_combo = QComboBox()
        self.alias_strategy_combo.setProperty("class", "view-binds-list")
        self.alias_strategy_combo.setMinimumWidth(320)
        self.alias_strategy_combo.setToolTip(
            "When two aliased devices both have a binding on the same control, "
            "choose whether to concatenate them into one string or demote the "
            "target's binding to a modifier."
        )
        current_alias = get_alias_strategy()
        for i, (value, label) in enumerate(ALIAS_STRATEGY_OPTIONS):
            self.alias_strategy_combo.addItem(label, value.value)
            if value == current_alias:
                self.alias_strategy_combo.setCurrentIndex(i)
        self.alias_strategy_combo.currentIndexChanged.connect(
            self._on_alias_strategy_changed
        )
        alias_label = QLabel("Alias merge strategy")
        alias_label.setObjectName("device_help_label")
        form.addRow(alias_label, self.alias_strategy_combo)

        # Profile inheritance strategy
        self.inheritance_strategy_combo = QComboBox()
        self.inheritance_strategy_combo.setProperty("class", "view-binds-list")
        self.inheritance_strategy_combo.setMinimumWidth(320)
        self.inheritance_strategy_combo.setToolTip(
            "When a child profile and an inherited parent profile both bind the "
            "same control, choose whether to keep only the child's binding, "
            "concatenate them, or demote the parent's binding to a modifier."
        )
        current_inheritance = get_inheritance_strategy()
        for i, (value, label) in enumerate(INHERITANCE_STRATEGY_OPTIONS):
            self.inheritance_strategy_combo.addItem(label, value.value)
            if value == current_inheritance:
                self.inheritance_strategy_combo.setCurrentIndex(i)
        self.inheritance_strategy_combo.currentIndexChanged.connect(
            self._on_inheritance_strategy_changed
        )
        inh_label = QLabel("Profile inheritance strategy")
        inh_label.setObjectName("device_help_label")
        form.addRow(inh_label, self.inheritance_strategy_combo)

        layout.addLayout(form)
        layout.addStretch(1)
        return tab

    def _on_open_after_export_changed(self, state: int):
        add_update_setting_value(
            OPEN_AFTER_EXPORT_SETTING_KEY,
            "true" if state == Qt.CheckState.Checked.value else "false",
        )

    def _on_date_format_changed(self, index: int):
        fmt = self.date_format_combo.currentData()
        if fmt:
            add_update_setting_value(DATE_FORMAT_SETTING_KEY, fmt)

    # Process-time settings (those that bake into the merged profile state)
    # must call appState.reprocess_profiles_with_notice(...) after persisting.
    # Export-time settings (date format, open-after-export) don't need this.
    def _on_alias_strategy_changed(self, index: int):
        value = self.alias_strategy_combo.currentData()
        if value:
            add_update_setting_value(ALIAS_CONFLICT_STRATEGY_KEY, value)
            self.appState.reprocess_profiles_with_notice(
                "Alias merge strategy updated — profiles reprocessed"
            )

    def _on_inheritance_strategy_changed(self, index: int):
        value = self.inheritance_strategy_combo.currentData()
        if value:
            add_update_setting_value(INHERITANCE_CONFLICT_STRATEGY_KEY, value)
            self.appState.reprocess_profiles_with_notice(
                "Inheritance merge strategy updated — profiles reprocessed"
            )

    # ── Shared Plugin Helpers ──

    @staticmethod
    def _get_trust_status(plugin_name: str, plugin_type: str) -> str:
        """Look up the trust status for a user-installed plugin."""
        from joystick_diagrams.db.db_plugin_trust import get_trust_reason
        from joystick_diagrams.ui.widgets.plugin_card import (
            TRUST_SIGNED,
            TRUST_UNTRUSTED,
            TRUST_USER_ACCEPTED,
        )

        reason = get_trust_reason(plugin_name, plugin_type)
        if reason == "signature_valid":
            return TRUST_SIGNED
        elif reason == "user_accepted":
            return TRUST_USER_ACCEPTED
        return TRUST_UNTRUSTED

    # ── Shared Plugin Install Helpers ──

    def _run_security_check(self, installed_path: Path, plugin_name: str) -> bool:
        """Run the signing/trust security check after installing a plugin.

        Returns True if the user accepted the plugin, False if they cancelled.
        """
        from joystick_diagrams.plugins.plugin_signing import verify_plugin_signature
        from joystick_diagrams.ui.plugin_security_dialog import (
            PluginSecurityWarningDialog,
            PluginSignedDialog,
        )

        if verify_plugin_signature(installed_path):
            dialog = PluginSignedDialog(plugin_name, self)
            dialog.exec()
            return True
        else:
            dialog = PluginSecurityWarningDialog(plugin_name, self)
            return dialog.exec() == PluginSecurityWarningDialog.Accepted

    def _record_trust(
        self, plugin_name: str, plugin_type: str, installed_path: Path
    ) -> None:
        """Record trust for a plugin after successful security check."""
        from joystick_diagrams.db.db_plugin_trust import set_plugin_trusted
        from joystick_diagrams.plugins.plugin_signing import verify_plugin_signature

        reason = (
            "signature_valid"
            if verify_plugin_signature(installed_path)
            else "user_accepted"
        )
        set_plugin_trusted(plugin_name, plugin_type, True, reason)

    def _show_conflict_banner(self, layout: QVBoxLayout, conflicts: list) -> None:
        """Add a yellow conflict warning banner if there are name conflicts."""
        if not conflicts:
            return

        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: #3D3520; border: 1px solid #F59E0B; "
            "border-radius: 6px; padding: 8px 12px; }"
        )
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(8, 6, 8, 6)
        banner_layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(
            qta.icon("fa5s.exclamation-triangle", color="#F59E0B").pixmap(16, 16)
        )
        icon_label.setFixedSize(16, 16)
        icon_label.setStyleSheet("background: transparent;")
        banner_layout.addWidget(icon_label)

        names = ", ".join(f"'{name}'" for name, _ in conflicts)
        text = QLabel(
            f"Skipped: {names} - a bundled plugin with the same name already exists."
        )
        text.setWordWrap(True)
        text.setStyleSheet("color: #F59E0B; background: transparent;")
        banner_layout.addWidget(text, stretch=1)

        layout.addWidget(banner)

    # ── Side Panel Helpers ──

    def _show_side_panel(self, panel_layout: QVBoxLayout, wrapper) -> None:
        """Show the config panel for a plugin in the given side panel layout."""
        from joystick_diagrams.ui.plugins_page import PluginConfigPanel

        self._clear_side_panel(panel_layout)
        panel = PluginConfigPanel(wrapper, self)
        panel.settings_changed.connect(self._on_side_panel_settings_changed)
        panel.close_requested.connect(lambda: self._clear_side_panel(panel_layout))
        panel_layout.addWidget(panel)

    def _clear_side_panel(self, panel_layout: QVBoxLayout) -> None:
        """Remove all widgets from a side panel layout."""
        while panel_layout.count():
            item = panel_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_side_panel_settings_changed(self):
        """Refresh status labels on all visible plugin cards."""
        for layout in (
            self._parser_plugin_cards_layout,
            self._output_plugin_cards_layout,
        ):
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), "refresh_status"):
                    item.widget().refresh_status()

    # ── Parser Plugins Tab ──

    def _create_parser_plugins_tab(self) -> QWidget:
        from joystick_diagrams.ui.widgets.drop_zone import DropZoneWidget

        tab = QWidget()
        tab_layout = QHBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        # Left column: header, buttons, drop zone, cards
        left = QWidget()
        layout = QVBoxLayout(left)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = SectionHeader("fa5s.puzzle-piece", "Parser Plugins")
        layout.addWidget(header)

        help_text = QLabel(
            "Parser plugins import joystick bindings from games and applications. "
            "Install additional parsers to support more games."
        )
        help_text.setObjectName("device_help_label")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # Conflict warnings
        self._parser_conflict_layout = QVBoxLayout()
        self._parser_conflict_layout.setSpacing(4)
        layout.addLayout(self._parser_conflict_layout)

        # Action buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        install_btn = QPushButton("Install Plugin")
        install_btn.setIcon(qta.icon("fa5s.file-import", color="white"))
        install_btn.setProperty("class", "plugin-setup-button")
        install_btn.clicked.connect(self._install_parser_plugin)
        button_row.addWidget(install_btn)

        url_btn = QPushButton("Install from URL")
        url_btn.setIcon(qta.icon("fa5s.link", color="white"))
        url_btn.setProperty("class", "plugin-setup-button")
        url_btn.clicked.connect(self._install_parser_plugin_from_url)
        button_row.addWidget(url_btn)

        open_folder_btn = QPushButton("Open Plugins Folder")
        open_folder_btn.setIcon(qta.icon("fa5s.folder-open", color="white"))
        open_folder_btn.setProperty("class", "plugin-setup-button")
        open_folder_btn.clicked.connect(
            lambda: webbrowser.open(str(utils.user_parser_plugins_root()))
        )
        button_row.addWidget(open_folder_btn)

        drop_zone = DropZoneWidget("Drop ZIP here", compact=True)
        drop_zone.file_dropped.connect(self._do_parser_install)
        button_row.addWidget(drop_zone)

        button_row.addStretch(1)
        layout.addLayout(button_row)

        # Plugin cards (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        cards_container = QWidget()
        self._parser_plugin_cards_layout = QVBoxLayout(cards_container)
        self._parser_plugin_cards_layout.setSpacing(4)
        self._parser_plugin_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._populate_parser_plugin_cards()

        scroll.setWidget(cards_container)
        layout.addWidget(scroll, 1)

        tab_layout.addWidget(left, 1)

        # Right column: side panel for plugin config
        self._parser_side_panel = QVBoxLayout()
        self._parser_side_panel.setContentsMargins(0, 0, 0, 0)
        tab_layout.addLayout(self._parser_side_panel)

        return tab

    def _populate_parser_plugin_cards(self):
        from joystick_diagrams.ui.widgets.plugin_card import TRUST_BUNDLED, PluginCard

        while self._parser_plugin_cards_layout.count():
            item = self._parser_plugin_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear and repopulate conflict banners
        while self._parser_conflict_layout.count():
            item = self._parser_conflict_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.appState.plugin_manager:
            return

        if self.appState.plugin_manager.conflicts:
            self._show_conflict_banner(
                self._parser_conflict_layout,
                self.appState.plugin_manager.conflicts,
            )

        for wrapper in self.appState.plugin_manager.plugin_wrappers:
            is_user = self.appState.plugin_manager.is_user_plugin(wrapper.name)
            trust_status = (
                self._get_trust_status(wrapper.name, "parser")
                if is_user
                else TRUST_BUNDLED
            )
            card = PluginCard(
                wrapper, is_user_plugin=is_user, trust_status=trust_status
            )
            card.config_requested.connect(
                lambda w: self._show_side_panel(self._parser_side_panel, w)
            )
            if is_user:
                card.uninstall_requested.connect(self._uninstall_parser_plugin)
            self._parser_plugin_cards_layout.addWidget(card)

        self._parser_plugin_cards_layout.addStretch(1)

    def _install_parser_plugin(self):
        result = QFileDialog.getOpenFileName(
            self,
            "Select Parser Plugin (ZIP)",
            str(Path.home()),
            "Plugin Archives (*.zip)",
        )
        if not result[0]:
            return

        self._do_parser_install(Path(result[0]))

    def _install_parser_plugin_from_url(self):
        url, ok = QInputDialog.getText(
            self,
            "Install Plugin from URL",
            "Enter the URL of a plugin ZIP file:",
        )
        if not ok or not url.strip():
            return

        self._do_parser_install(url.strip())

    def _do_parser_install(self, source: Path | str):
        from joystick_diagrams.plugins.plugin_installer import (
            install_plugin,
            validate_plugin,
        )

        try:
            installed_path = install_plugin(source, "parser")
        except Exception as e:
            QMessageBox.warning(self, "Install Failed", str(e))
            return

        valid, msg = validate_plugin(installed_path, "parser")
        if not valid:
            shutil.rmtree(installed_path, ignore_errors=True)
            QMessageBox.warning(self, "Invalid Plugin", msg)
            return

        # Check name conflict with bundled plugins
        if self.appState.plugin_manager:
            bundled_names = {
                w.name
                for w in self.appState.plugin_manager.plugin_wrappers
                if not self.appState.plugin_manager.is_user_plugin(w.name)
            }
            if msg in bundled_names:
                shutil.rmtree(installed_path, ignore_errors=True)
                QMessageBox.warning(
                    self,
                    "Name Conflict",
                    f"A bundled plugin named '{msg}' already exists. "
                    f"The user plugin cannot be installed.",
                )
                return

        # Security check
        if not self._run_security_check(installed_path, msg):
            shutil.rmtree(installed_path, ignore_errors=True)
            return

        self._record_trust(msg, "parser", installed_path)

        QMessageBox.information(
            self, "Plugin Installed", f"Parser plugin '{msg}' installed successfully."
        )
        self._reload_parser_plugins()

    def _uninstall_parser_plugin(self, name: str):
        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            f"Remove the plugin '{name}'? Plugin settings will be preserved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from joystick_diagrams.plugins.plugin_installer import uninstall_plugin

        path = self.appState.plugin_manager.get_user_plugin_path(name)
        if path:
            try:
                uninstall_plugin(name, path, "parser")
                self._reload_parser_plugins()
            except Exception as e:
                QMessageBox.warning(self, "Uninstall Failed", str(e))

    def _reload_parser_plugins(self):
        from joystick_diagrams.plugins.plugin_manager import ParserPluginManager

        mgr = ParserPluginManager()
        mgr.load_discovered_plugins()
        mgr.create_plugin_wrappers()
        self.appState.plugin_manager = mgr
        self._populate_parser_plugin_cards()

        # Refresh the Setup/PluginsPage if it exists
        main_window = self.appState.main_window
        if (
            main_window
            and hasattr(main_window, "_setup_page")
            and main_window._setup_page
        ):
            main_window._setup_page.populate_plugin_cards()

    # ── Output Plugins Tab ──

    def _create_output_plugins_tab(self) -> QWidget:
        from joystick_diagrams.ui.widgets.drop_zone import DropZoneWidget

        tab = QWidget()
        tab_layout = QHBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        # Left column: header, buttons, drop zone, cards
        left = QWidget()
        layout = QVBoxLayout(left)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = SectionHeader("fa5s.plug", "Output Plugins")
        layout.addWidget(header)

        help_text = QLabel(
            "Output plugins run automatically after export to deliver your diagrams "
            "to other applications (e.g. OpenKneeboard)."
        )
        help_text.setObjectName("device_help_label")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # Conflict warnings
        self._output_conflict_layout = QVBoxLayout()
        self._output_conflict_layout.setSpacing(4)
        layout.addLayout(self._output_conflict_layout)

        # Action buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        install_btn = QPushButton("Install Plugin")
        install_btn.setIcon(qta.icon("fa5s.file-import", color="white"))
        install_btn.setProperty("class", "plugin-setup-button")
        install_btn.clicked.connect(self._install_output_plugin)
        button_row.addWidget(install_btn)

        url_btn = QPushButton("Install from URL")
        url_btn.setIcon(qta.icon("fa5s.link", color="white"))
        url_btn.setProperty("class", "plugin-setup-button")
        url_btn.clicked.connect(self._install_output_plugin_from_url)
        button_row.addWidget(url_btn)

        open_folder_btn = QPushButton("Open Plugins Folder")
        open_folder_btn.setIcon(qta.icon("fa5s.folder-open", color="white"))
        open_folder_btn.setProperty("class", "plugin-setup-button")
        open_folder_btn.clicked.connect(self._open_output_plugins_folder)
        button_row.addWidget(open_folder_btn)

        drop_zone = DropZoneWidget("Drop ZIP here", compact=True)
        drop_zone.file_dropped.connect(self._do_output_install)
        button_row.addWidget(drop_zone)

        button_row.addStretch(1)
        layout.addLayout(button_row)

        # Plugin cards (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        cards_container = QWidget()
        self._output_plugin_cards_layout = QVBoxLayout(cards_container)
        self._output_plugin_cards_layout.setSpacing(4)
        self._output_plugin_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._populate_output_plugin_cards()

        scroll.setWidget(cards_container)
        layout.addWidget(scroll, 1)

        tab_layout.addWidget(left, 1)

        # Right column: side panel for plugin config
        self._output_side_panel = QVBoxLayout()
        self._output_side_panel.setContentsMargins(0, 0, 0, 0)
        tab_layout.addLayout(self._output_side_panel)

        return tab

    def _populate_output_plugin_cards(self):
        from joystick_diagrams.ui.widgets.plugin_card import TRUST_BUNDLED, PluginCard

        while self._output_plugin_cards_layout.count():
            item = self._output_plugin_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear and repopulate conflict banners
        while self._output_conflict_layout.count():
            item = self._output_conflict_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.appState.output_plugin_manager:
            return

        if self.appState.output_plugin_manager.conflicts:
            self._show_conflict_banner(
                self._output_conflict_layout,
                self.appState.output_plugin_manager.conflicts,
            )

        for wrapper in self.appState.output_plugin_manager.plugin_wrappers:
            is_user = self.appState.output_plugin_manager.is_user_plugin(wrapper.name)
            trust_status = (
                self._get_trust_status(wrapper.name, "output")
                if is_user
                else TRUST_BUNDLED
            )
            card = PluginCard(
                wrapper, is_user_plugin=is_user, trust_status=trust_status
            )
            card.config_requested.connect(
                lambda w: self._show_side_panel(self._output_side_panel, w)
            )
            if is_user:
                card.uninstall_requested.connect(self._uninstall_output_plugin)
            self._output_plugin_cards_layout.addWidget(card)

        self._output_plugin_cards_layout.addStretch(1)

    def _install_output_plugin(self):
        result = QFileDialog.getOpenFileName(
            self,
            "Select Output Plugin (ZIP)",
            str(Path.home()),
            "Plugin Archives (*.zip)",
        )
        if not result[0]:
            return

        self._do_output_install(Path(result[0]))

    def _install_output_plugin_from_url(self):
        url, ok = QInputDialog.getText(
            self,
            "Install Plugin from URL",
            "Enter the URL of a plugin ZIP file:",
        )
        if not ok or not url.strip():
            return

        self._do_output_install(url.strip())

    def _do_output_install(self, source: Path | str):
        from joystick_diagrams.plugins.plugin_installer import (
            install_plugin,
            validate_plugin,
        )

        try:
            installed_path = install_plugin(source, "output")
        except Exception as e:
            QMessageBox.warning(self, "Install Failed", str(e))
            return

        valid, msg = validate_plugin(installed_path, "output")
        if not valid:
            shutil.rmtree(installed_path, ignore_errors=True)
            QMessageBox.warning(self, "Invalid Plugin", msg)
            return

        # Check name conflict with bundled plugins
        if self.appState.output_plugin_manager:
            bundled_names = {
                w.name
                for w in self.appState.output_plugin_manager.plugin_wrappers
                if not self.appState.output_plugin_manager.is_user_plugin(w.name)
            }
            if msg in bundled_names:
                shutil.rmtree(installed_path, ignore_errors=True)
                QMessageBox.warning(
                    self,
                    "Name Conflict",
                    f"A bundled plugin named '{msg}' already exists. "
                    f"The user plugin cannot be installed.",
                )
                return

        # Security check
        if not self._run_security_check(installed_path, msg):
            shutil.rmtree(installed_path, ignore_errors=True)
            return

        self._record_trust(msg, "output", installed_path)

        QMessageBox.information(
            self, "Plugin Installed", f"Output plugin '{msg}' installed successfully."
        )
        self._reload_output_plugins()

    def _uninstall_output_plugin(self, name: str):
        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            f"Remove the plugin '{name}'? Plugin settings will be preserved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from joystick_diagrams.plugins.plugin_installer import uninstall_plugin

        path = self.appState.output_plugin_manager.get_user_plugin_path(name)
        if path:
            try:
                uninstall_plugin(name, path, "output")
                self._reload_output_plugins()
            except Exception as e:
                QMessageBox.warning(self, "Uninstall Failed", str(e))

    def _reload_output_plugins(self):
        from joystick_diagrams.plugins.output_plugin_manager import OutputPluginManager

        mgr = OutputPluginManager()
        mgr.load_discovered_plugins()
        mgr.create_plugin_wrappers()
        self.appState.output_plugin_manager = mgr
        self._populate_output_plugin_cards()

    def _open_output_plugins_folder(self):
        webbrowser.open(str(utils.user_output_plugins_root()))


if __name__ == "__main__":
    pass
