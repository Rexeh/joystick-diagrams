"""3. Bindings › Labels: every label (your own text for an action on your diagrams).

Labels stay global (one label per game action). The "Only labels used on
[controller]" filter narrows the table to labels whose action is bound on that
controller in any profile.
"""

from __future__ import annotations

import logging
from typing import Any

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.ui import strings_bindings as S

_logger = logging.getLogger(__name__)

ALL_CONTROLLERS_KEY = ""


def actions_used_on(device_guid: str, profile_wrappers: list[Any]) -> set[str]:
    """Every action (main or modifier) bound on ``device_guid`` in any profile."""
    actions: set[str] = set()
    for wrapper in profile_wrappers:
        profile = getattr(wrapper, "profile", None)
        devices = getattr(profile, "devices", None) or {}
        device = devices.get(device_guid)
        if device is None:
            continue
        for input_obj in device.get_combined_inputs().values():
            if input_obj.command:
                actions.add(input_obj.command)
            for modifier in input_obj.modifiers:
                if modifier.command:
                    actions.add(modifier.command)
    return actions


def controllers_in(profile_wrappers: list[Any]) -> list[tuple[str, str]]:
    """``(guid, name)`` for every controller bound in any profile, by name."""
    found: dict[str, str] = {}
    for wrapper in profile_wrappers:
        profile = getattr(wrapper, "profile", None)
        devices = getattr(profile, "devices", None) or {}
        for guid, device in devices.items():
            found.setdefault(guid, getattr(device, "name", guid))
    return sorted(found.items(), key=lambda item: item[1].casefold())


class CustomiseLabels(QWidget):
    """Standalone screen for managing labels."""

    labels_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()
        self._filter_guid: str = ALL_CONTROLLERS_KEY
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        help_text = QLabel(S.LABELS_INTRO)
        help_text.setObjectName("device_help_label")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filter_label = QLabel(S.LABELS_FILTER)
        filter_label.setStyleSheet("font-weight: bold;")
        filter_row.addWidget(filter_label)
        self.filter_combo = QComboBox()
        self.filter_combo.setProperty("class", "view-binds-list")
        self.filter_combo.setAccessibleName(S.LABELS_FILTER)
        self.filter_combo.setMinimumWidth(260)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.filter_combo)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([S.COLUMN_ACTION, S.COLUMN_LABEL, ""])
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
        # The table and its empty state share one slot that takes the stretch, so
        # the help, filter and add rows never move when the table is empty.
        self.table_stack = QStackedWidget()
        self.table_stack.addWidget(self.table)
        layout.addWidget(self.table_stack, 1)

        self._label_count_text = QLabel()
        self._label_count_text.setObjectName("device_help_label")
        layout.addWidget(self._label_count_text)

        self._empty_label = QLabel(S.LABELS_EMPTY)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet(
            "color: #9AA0A6; font-style: italic; padding: 20px;"
        )
        self.table_stack.addWidget(self._empty_label)

        # Add row
        add_row_layout = QHBoxLayout()
        add_row_layout.setSpacing(8)
        line_edit_style = (
            "QLineEdit { color: #E8EAED; background-color: #252830; "
            "border: 1px solid #3C4043; border-radius: 4px; padding: 8px 12px; }"
            "QLineEdit:focus { border-color: #4C8BF5; }"
            "QLineEdit::placeholder { color: #6B7280; }"
        )
        self.original_input = QLineEdit()
        self.original_input.setPlaceholderText(S.LABELS_ACTION_PLACEHOLDER)
        self.original_input.setAccessibleName(S.COLUMN_ACTION)
        self.original_input.setStyleSheet(line_edit_style)
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText(S.LABELS_LABEL_PLACEHOLDER)
        self.custom_input.setAccessibleName(S.COLUMN_LABEL)
        self.custom_input.setStyleSheet(line_edit_style)
        self.add_button = QPushButton(S.LABELS_ADD)
        self.add_button.setIcon(qta.icon("fa5s.plus", color="white"))
        self.add_button.setIconSize(QSize(14, 14))
        self.add_button.setProperty("class", "plugin-setup-button")
        self.add_button.clicked.connect(self.add_manual_entry)
        add_row_layout.addWidget(self.original_input, 1)
        add_row_layout.addWidget(self.custom_input, 1)
        add_row_layout.addWidget(self.add_button)
        layout.addLayout(add_row_layout)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.reset_all_button = QPushButton(S.LABELS_REMOVE_ALL)
        self.reset_all_button.setIcon(qta.icon("fa5s.undo", color="white"))
        self.reset_all_button.setIconSize(QSize(14, 14))
        self.reset_all_button.setProperty("class", "plugin-setup-button")
        self.reset_all_button.clicked.connect(self.reset_all_labels)
        button_row.addWidget(self.reset_all_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

    # ── Refresh ──

    def refresh(self):
        self._reload_filter()
        self.populate_table()

    def _reload_filter(self) -> None:
        wanted = self._filter_guid
        self._loading = True
        try:
            self.filter_combo.clear()
            self.filter_combo.addItem(S.LABELS_FILTER_ALL, ALL_CONTROLLERS_KEY)
            service = self.appState.device_service
            for guid, name in controllers_in(self.appState.profile_wrappers):
                self.filter_combo.addItem(service.resolve_name(guid, name), guid)
            index = self.filter_combo.findData(wanted)
            self.filter_combo.setCurrentIndex(max(index, 0))
            if index < 0:
                self._filter_guid = ALL_CONTROLLERS_KEY
        finally:
            self._loading = False

    def set_filter_device(self, device_guid: str | None) -> None:
        """Show only labels used on ``device_guid`` (``None``/"" for all)."""
        self._filter_guid = device_guid or ALL_CONTROLLERS_KEY
        index = self.filter_combo.findData(self._filter_guid)
        if index >= 0 and index != self.filter_combo.currentIndex():
            self.filter_combo.setCurrentIndex(index)  # populates through the signal
        else:
            self.populate_table()

    def _on_filter_changed(self, index: int) -> None:
        if self._loading:
            return
        self._filter_guid = self.filter_combo.currentData() or ALL_CONTROLLERS_KEY
        self.populate_table()

    def filtered_labels(self) -> dict[str, str]:
        labels = self.appState.label_service.get_all_custom_labels()
        if not self._filter_guid:
            return dict(labels)
        used = actions_used_on(self._filter_guid, self.appState.profile_wrappers)
        return {k: v for k, v in labels.items() if k in used}

    def populate_table(self):
        self.table.blockSignals(True)
        labels = self.filtered_labels()
        all_count = len(self.appState.label_service.get_all_custom_labels())
        self.table.setRowCount(len(labels))

        count = len(labels)
        if count > 0:
            self._label_count_text.setText(
                S.LABEL_COUNT.format(count=count, labels=S.plural(count, *S.LABELS))
            )
            self.table_stack.setCurrentWidget(self.table)
        else:
            self._label_count_text.setText("")
            if self._filter_guid and all_count:
                self._empty_label.setText(
                    S.LABELS_EMPTY_FILTERED.format(
                        controller=self.filter_combo.currentText()
                    )
                )
            else:
                self._empty_label.setText(S.LABELS_EMPTY)
            self.table_stack.setCurrentWidget(self._empty_label)

        for row, (original, custom) in enumerate(sorted(labels.items())):
            original_item = QTableWidgetItem(original)
            original_item.setFlags(original_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, original_item)
            custom_item = QTableWidgetItem(custom)
            self.table.setItem(row, 1, custom_item)
            self._add_delete_button(row, original)

        self.reset_all_button.setEnabled(all_count > 0)
        self.table.blockSignals(False)

    def _add_delete_button(self, row: int, original: str):
        reset_button = QPushButton()
        reset_button.setIcon(qta.icon("fa5s.trash-alt", color="#F87171"))
        reset_button.setIconSize(QSize(16, 16))
        reset_button.setToolTip(S.LABELS_REMOVE_TIP)
        reset_button.setAccessibleName(S.LABELS_REMOVE_TIP)
        reset_button.setFixedSize(QSize(36, 36))
        reset_button.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            "QPushButton:hover { background: rgba(248, 113, 113, 0.15); border-radius: 4px; }"
        )
        reset_button.clicked.connect(lambda checked, o=original: self.reset_label(o))
        self.table.setCellWidget(row, 2, reset_button)

    # ── Edits ──

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
        self.labels_changed.emit()

    def add_manual_entry(self):
        original = self.original_input.text().strip()
        custom = self.custom_input.text().strip()
        if not original or not custom:
            return
        self.appState.label_service.set_label(original, custom)
        self.original_input.clear()
        self.custom_input.clear()
        self.populate_table()
        self.labels_changed.emit()

    def reset_label(self, original: str):
        self.appState.label_service.remove_label(original)
        self.populate_table()
        self.labels_changed.emit()

    def reset_all_labels(self):
        box = QMessageBox(self)
        box.setWindowTitle(S.LABELS_REMOVE_ALL_TITLE)
        box.setText(S.LABELS_REMOVE_ALL_TITLE)
        box.setInformativeText(S.LABELS_REMOVE_ALL_TEXT)
        remove = box.addButton(
            S.LABELS_REMOVE_ALL, QMessageBox.ButtonRole.DestructiveRole
        )
        box.addButton(S.CANCEL, QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not remove:
            return
        self.appState.label_service.remove_all_labels()
        self.populate_table()
        self.labels_changed.emit()


if __name__ == "__main__":
    pass
