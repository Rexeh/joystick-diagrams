"""4. Diagrams › Pages: the combined pages (journey board J12).

A list of pages, each row its name over a one-line summary ("Side by side ·
A4 landscape · 12 profiles"), with New page…, Edit…, Rename, Duplicate, Delete
and Edit in Layout ›. New and Edit open ``PagesDialog``; Edit in Layout › opens
the page in 4. Diagrams › Layout with its Page panel, where every field saves as
it changes. v1 places a page by its arrangement (free placement comes later).
"""

from __future__ import annotations

import logging
from typing import Any

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.render.page import ARRANGEMENT_LABELS
from joystick_diagrams.ui import strings_diagrams as S
from joystick_diagrams.ui.device_setup import page_size_text

_logger = logging.getLogger(__name__)

PAGE_ID_ROLE = Qt.ItemDataRole.UserRole


def page_summary(page: Any, profile_count: int) -> str:
    """ "Side by side · A4 landscape · 12 profiles"."""
    return S.PAGES_SUMMARY.format(
        size=page_size_text(page),
        arrangement=ARRANGEMENT_LABELS.get(page.arrangement, ""),
        profiles=profile_count,
        profiles_word=S.plural(profile_count, *S.PROFILES),
    )


class PagesPage(QWidget):
    pages_changed = Signal()
    page_created = Signal(str)  # page id (from New page…)
    layout_requested = Signal(str)  # page id

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()
        self.service = self.appState.page_service
        self._devices: list[Any] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 12)
        root.setSpacing(10)
        heading = QLabel(S.NAV_PAGES)
        heading.setObjectName("heading_label")
        root.addWidget(heading)
        intro = QLabel(S.PAGES_INTRO)
        intro.setObjectName("device_help_label")
        intro.setWordWrap(True)
        root.addWidget(intro)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.new_button = self._button(S.PAGES_NEW, "fa5s.plus", self.new_page)
        self.edit_button = self._button(S.PAGES_EDIT, "fa5s.pen", self.edit_page)
        self.rename_button = self._button(S.PAGES_RENAME, None, self.rename_page)
        self.duplicate_button = self._button(
            S.PAGES_DUPLICATE, "fa5s.copy", self.duplicate_page
        )
        self.delete_button = self._button(
            S.PAGES_DELETE, "fa5s.trash-alt", self.delete_page
        )
        self.layout_button = self._button(
            S.PAGES_EDIT_LAYOUT, None, self._request_layout
        )
        for button in (
            self.new_button,
            self.edit_button,
            self.rename_button,
            self.duplicate_button,
            self.delete_button,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        toolbar.addWidget(self.layout_button)
        root.addLayout(toolbar)

        self.list = QListWidget()
        self.list.setAccessibleName(S.NAV_PAGES)
        self.list.currentRowChanged.connect(lambda _r: self._update_buttons())
        self.list.itemDoubleClicked.connect(lambda _i: self.edit_page())
        self.empty_label = QLabel(S.PAGES_EMPTY)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("color: #9AA0A6; padding: 24px;")
        # The list and its empty state share the stretching slot
        self.list_stack = QStackedWidget()
        self.list_stack.addWidget(self.list)
        self.list_stack.addWidget(self.empty_label)
        root.addWidget(self.list_stack, 1)
        self._update_buttons()

    def _button(self, text: str, icon: str | None, slot) -> QPushButton:
        button = QPushButton(text)
        if icon:
            button.setIcon(qta.icon(icon, color="white"))
            button.setIconSize(QSize(12, 12))
        button.setProperty("class", "plugin-setup-button")
        button.clicked.connect(slot)
        return button

    # ── Refresh ──

    def refresh(self) -> None:
        from joystick_diagrams.export import page_profiles

        try:
            from joystick_diagrams.ui.device_setup_controller import get_export_devices

            self._devices = list(get_export_devices())
        except Exception as error:  # noqa: BLE001
            _logger.warning(f"Could not load controllers: {error}")
            self._devices = []
        current = self.current_page_id()
        self.list.clear()
        for page in self.service.pages():
            try:
                profiles = len(page_profiles(page, self._devices))
            except Exception:  # noqa: BLE001
                profiles = 0
            item = QListWidgetItem(
                qta.icon("fa5s.object-group", color="#9AA0A6"),
                f"{page.name}\n{page_summary(page, profiles)}",
            )
            item.setData(PAGE_ID_ROLE, page.page_id)
            item.setSizeHint(QSize(0, 52))
            self.list.addItem(item)
            if page.page_id == current:
                self.list.setCurrentItem(item)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)
        has_pages = self.list.count() > 0
        self.list_stack.setCurrentWidget(self.list if has_pages else self.empty_label)
        self._update_buttons()

    def current_page_id(self) -> str | None:
        item = self.list.currentItem()
        return item.data(PAGE_ID_ROLE) if item is not None else None

    def select_page(self, page_id: str) -> None:
        for row in range(self.list.count()):
            if self.list.item(row).data(PAGE_ID_ROLE) == page_id:
                self.list.setCurrentRow(row)
                return

    def _update_buttons(self) -> None:
        has = self.current_page_id() is not None
        for button in (
            self.edit_button,
            self.rename_button,
            self.duplicate_button,
            self.delete_button,
            self.layout_button,
        ):
            button.setEnabled(has)

    # ── Actions ──

    def open_dialog(self, page=None, preselect: list[str] | None = None):
        """The Combine dialog (create or edit); the saved page or ``None``."""
        from joystick_diagrams.ui.pages_dialog import PagesDialog

        dialog = PagesDialog(
            self, page, export_devices=self._devices, preselect=preselect
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.page

    def new_page(self) -> None:
        page = self.open_dialog()
        if page is None:
            return
        self.refresh()
        self.select_page(page.page_id)
        self.pages_changed.emit()
        self.page_created.emit(page.page_id)

    def edit_page(self) -> None:
        page_id = self.current_page_id()
        page = self.service.get(page_id) if page_id else None
        if page is None:
            return
        if self.open_dialog(page) is not None:
            self.refresh()
            self.pages_changed.emit()

    def rename_page(self) -> None:
        page_id = self.current_page_id()
        page = self.service.get(page_id) if page_id else None
        if page is None:
            return
        name, ok = QInputDialog.getText(
            self, S.PAGES_RENAME_TITLE, S.PAGES_RENAME_LABEL, text=page.name
        )
        if not ok or not name.strip() or name.strip() == page.name:
            return
        try:
            self.service.rename(page_id, name)
        except ValueError as error:
            QMessageBox.warning(self, S.PAGES_RENAME_TITLE, str(error))
            return
        self.refresh()
        self.pages_changed.emit()

    def duplicate_page(self) -> None:
        page_id = self.current_page_id()
        if not page_id:
            return
        try:
            copy = self.service.duplicate(page_id)
        except ValueError as error:
            QMessageBox.warning(self, S.PAGES_DUPLICATE, str(error))
            return
        self.refresh()
        self.select_page(copy.page_id)
        self.pages_changed.emit()

    def delete_page(self) -> None:
        page_id = self.current_page_id()
        page = self.service.get(page_id) if page_id else None
        if page is None:
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(S.PAGES_DELETE_TITLE.format(page=page.name))
        box.setText(S.PAGES_DELETE_TITLE.format(page=page.name))
        box.setInformativeText(S.PAGES_DELETE_TEXT)
        delete = box.addButton(
            S.PAGES_DELETE_BUTTON, QMessageBox.ButtonRole.DestructiveRole
        )
        box.addButton(S.CANCEL, QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not delete:
            return
        self.service.delete(page_id)
        self.refresh()
        self.pages_changed.emit()

    def _request_layout(self) -> None:
        page_id = self.current_page_id()
        if page_id:
            self.layout_requested.emit(page_id)


if __name__ == "__main__":
    pass
