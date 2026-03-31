import logging
import shutil
import webbrowser
from datetime import datetime
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams import utils
from joystick_diagrams.app_state import AppState
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
            ("fa5s.eye-slash", "Hidden Devices"),
            ("fa5s.tags", "Custom Labels"),
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
        self.stack.addWidget(self._create_hidden_devices_tab())
        self.stack.addWidget(self._create_custom_labels_tab())
        self.stack.addWidget(self._create_parser_plugins_tab())
        self.stack.addWidget(self._create_output_plugins_tab())
        root_layout.addWidget(self.stack, 1)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

    def refresh(self):
        """Refresh data-dependent tabs when returning to this page."""
        self.populate_hidden_table()
        self.populate_table()
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

    # ── Hidden Devices Tab ──

    def _create_hidden_devices_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = SectionHeader("fa5s.eye-slash", "Hidden Devices")
        layout.addWidget(header)

        help_text = QLabel(
            "Devices listed below are hidden from the Customise and Export views. "
            "Right-click a device in the Customise tab to hide it."
        )
        help_text.setObjectName("device_help_label")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        self.hidden_table = QTableWidget()
        self.hidden_table.setColumnCount(3)
        self.hidden_table.setHorizontalHeaderLabels(["Device Name", "GUID", ""])
        self.hidden_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.hidden_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.hidden_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.hidden_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.hidden_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.hidden_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.hidden_table.verticalHeader().setVisible(False)
        self.hidden_table.verticalHeader().setDefaultSectionSize(40)
        self.hidden_table.setProperty("class", "view-binds-tree")
        layout.addWidget(self.hidden_table)

        self.populate_hidden_table()
        return tab

    def populate_hidden_table(self):
        hidden = self.appState.device_service.get_all_hidden()

        if not hidden:
            self.hidden_table.setRowCount(0)
            self.hidden_table.hide()
            if not hasattr(self, "_hidden_empty_label"):
                self._hidden_empty_label = QLabel(
                    "No hidden devices. Right-click a device in the Customise tab to hide it."
                )
                self._hidden_empty_label.setObjectName("device_help_label")
                self._hidden_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._hidden_empty_label.setWordWrap(True)
                self._hidden_empty_label.setStyleSheet(
                    "color: #9AA0A6; font-style: italic; padding: 40px;"
                )
                # Insert after the table in the parent layout
                self.hidden_table.parent().layout().addWidget(self._hidden_empty_label)
            self._hidden_empty_label.show()
            return

        if hasattr(self, "_hidden_empty_label"):
            self._hidden_empty_label.hide()
        self.hidden_table.show()
        self.hidden_table.setRowCount(len(hidden))

        for row, (guid, name) in enumerate(sorted(hidden.items(), key=lambda x: x[1])):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.hidden_table.setItem(row, 0, name_item)

            guid_item = QTableWidgetItem(guid)
            guid_item.setFlags(guid_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.hidden_table.setItem(row, 1, guid_item)

            unhide_button = QPushButton()
            unhide_button.setText("Unhide")
            unhide_button.setIcon(qta.icon("fa5s.eye", color="white"))
            unhide_button.setIconSize(QSize(14, 14))
            unhide_button.setProperty("class", "plugin-setup-button")
            unhide_button.clicked.connect(
                lambda checked, g=guid, n=name: self.unhide_device(g, n)
            )
            self.hidden_table.setCellWidget(row, 2, unhide_button)

    def unhide_device(self, guid: str, name: str):
        self.appState.device_service.set_hidden(guid, name, False)
        self.populate_hidden_table()

    # ── Custom Labels Tab ──

    def _create_custom_labels_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = SectionHeader("fa5s.tags", "Custom Labels")
        layout.addWidget(header)

        help_text = QLabel(
            "Manage your custom labels below. "
            "Double-click a Custom Label cell to edit it, "
            "or add a new manual mapping at the bottom."
        )
        help_text.setObjectName("device_help_label")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Original Command", "Custom Label", ""])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setProperty("class", "view-binds-tree")
        self.table.cellChanged.connect(self.on_cell_changed)
        layout.addWidget(self.table)

        # Label count
        self._label_count_text = QLabel()
        self._label_count_text.setObjectName("device_help_label")
        layout.addWidget(self._label_count_text)

        # Empty state for labels
        self._labels_empty_label = QLabel(
            "No custom labels. Double-click an action in the Customise tab to rename it."
        )
        self._labels_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._labels_empty_label.setWordWrap(True)
        self._labels_empty_label.setStyleSheet(
            "color: #9AA0A6; font-style: italic; padding: 20px;"
        )
        self._labels_empty_label.hide()
        layout.addWidget(self._labels_empty_label)

        # Add manual entry row
        add_row_layout = QHBoxLayout()
        add_row_layout.setSpacing(8)

        line_edit_style = (
            "QLineEdit {"
            "  color: #E8EAED;"
            "  background-color: #252830;"
            "  border: 1px solid #3C4043;"
            "  border-radius: 4px;"
            "  padding: 8px 12px;"
            "}"
            "QLineEdit:focus {"
            "  border-color: #4C8BF5;"
            "}"
            "QLineEdit::placeholder {"
            "  color: #6B7280;"
            "}"
        )

        self.original_input = QLineEdit()
        self.original_input.setPlaceholderText("Original command text...")
        self.original_input.setStyleSheet(line_edit_style)

        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Custom label...")
        self.custom_input.setStyleSheet(line_edit_style)

        self.add_button = QPushButton()
        self.add_button.setText("Add")
        self.add_button.setIcon(qta.icon("fa5s.plus", color="white"))
        self.add_button.setIconSize(QSize(14, 14))
        self.add_button.setProperty("class", "plugin-setup-button")
        self.add_button.clicked.connect(self.add_manual_entry)

        add_row_layout.addWidget(self.original_input, 1)
        add_row_layout.addWidget(self.custom_input, 1)
        add_row_layout.addWidget(self.add_button)
        layout.addLayout(add_row_layout)

        # Reset all button
        button_row = QHBoxLayout()
        button_row.addStretch(1)

        self.reset_all_button = QPushButton()
        self.reset_all_button.setText("Reset All Labels")
        self.reset_all_button.setIcon(qta.icon("fa5s.undo", color="white"))
        self.reset_all_button.setIconSize(QSize(14, 14))
        self.reset_all_button.setProperty("class", "run-button")
        self.reset_all_button.clicked.connect(self.reset_all_labels)
        button_row.addWidget(self.reset_all_button)

        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.populate_table()
        return tab

    def populate_table(self):
        self.table.blockSignals(True)
        labels = self.appState.label_service.get_all_custom_labels()
        self.table.setRowCount(len(labels))

        # Update count and empty state
        count = len(labels)
        if count > 0:
            self._label_count_text.setText(
                f"{count} custom label{'s' if count != 1 else ''}"
            )
            self._label_count_text.show()
            self._labels_empty_label.hide()
            self.table.show()
        else:
            self._label_count_text.hide()
            self._labels_empty_label.show()
            self.table.hide()

        for row, (original, custom) in enumerate(sorted(labels.items())):
            original_item = QTableWidgetItem(original)
            original_item.setFlags(original_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, original_item)

            custom_item = QTableWidgetItem(custom)
            self.table.setItem(row, 1, custom_item)

            self._add_delete_button(row, original)

        self.reset_all_button.setEnabled(len(labels) > 0)
        self.table.blockSignals(False)

    def _add_delete_button(self, row: int, original: str):
        reset_button = QPushButton()
        reset_button.setIcon(qta.icon("fa5s.trash-alt", color="#EF4444"))
        reset_button.setIconSize(QSize(16, 16))
        reset_button.setToolTip("Remove custom label")
        reset_button.setFixedSize(QSize(36, 36))
        reset_button.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            "QPushButton:hover { background: rgba(239, 68, 68, 0.15); border-radius: 4px; }"
        )
        reset_button.clicked.connect(lambda checked, o=original: self.reset_label(o))
        self.table.setCellWidget(row, 2, reset_button)

    def on_cell_changed(self, row: int, column: int):
        if column != 1:
            return

        original_item = self.table.item(row, 0)
        custom_item = self.table.item(row, 1)
        if not original_item or not custom_item:
            return

        original = original_item.text()
        new_text = custom_item.text().strip()

        if not new_text or new_text == original:
            self.appState.label_service.remove_label(original)
            self.populate_table()
        else:
            self.appState.label_service.set_label(original, new_text)

    def add_manual_entry(self):
        original = self.original_input.text().strip()
        custom = self.custom_input.text().strip()

        if not original or not custom:
            return

        self.appState.label_service.set_label(original, custom)
        self.original_input.clear()
        self.custom_input.clear()
        self.populate_table()

    def reset_label(self, original: str):
        self.appState.label_service.remove_label(original)
        self.populate_table()

    def reset_all_labels(self):
        self.appState.label_service.remove_all_labels()
        self.populate_table()

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
