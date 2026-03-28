import logging
from datetime import datetime

import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db.db_settings import add_update_setting_value, get_setting

_logger = logging.getLogger(__name__)

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
        root_layout.addWidget(self.stack, 1)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

    # ── General Tab ──

    def _create_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

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

        layout.addLayout(form)
        layout.addStretch(1)
        return tab

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


if __name__ == "__main__":
    pass
