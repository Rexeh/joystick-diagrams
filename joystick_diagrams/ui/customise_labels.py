import logging

import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState

_logger = logging.getLogger(__name__)


class CustomiseLabels(QWidget):
    """Standalone screen for managing custom labels."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        help_text = QLabel(
            "Manage your custom labels below. "
            "Double-click a Custom Label cell to edit it, "
            "or add a new manual mapping at the bottom. "
            "You can also double-click actions in the Profiles binds tree to rename them inline."
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

        # Empty state
        self._empty_label = QLabel(
            "No custom labels yet. Double-click an action in the Profiles binds tree to rename it, "
            "or add a manual mapping below."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet(
            "color: #9AA0A6; font-style: italic; padding: 20px;"
        )
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

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

    def refresh(self):
        self.populate_table()

    def populate_table(self):
        self.table.blockSignals(True)
        labels = self.appState.label_service.get_all_custom_labels()
        self.table.setRowCount(len(labels))

        count = len(labels)
        if count > 0:
            self._label_count_text.setText(
                f"{count} custom label{'s' if count != 1 else ''}"
            )
            self._label_count_text.show()
            self._empty_label.hide()
            self.table.show()
        else:
            self._label_count_text.hide()
            self._empty_label.show()
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


if __name__ == "__main__":
    pass
