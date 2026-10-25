"""The settings rows under the Export list (journey boards J08, J09, J14 #7).

Format [SVG | PNG | PDF] · Style "<active style> · Change…" (opens Appearance)
· Save to ("Not chosen yet. We'll ask when you export." until a folder is chosen,
then the folder · Change…) · Also send to (the other apps that get each export,
"OpenKneeboard · On · Change…").

There is no default export folder. ``ask_for_folder`` opens the system folder
dialog pre-filled with ``suggested_export_folder()`` (Windows: Documents,
macOS/Linux: home, plus "Joystick Diagrams"); the choice is remembered in
``workflow_settings``.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from joystick_diagrams import workflow_settings
from joystick_diagrams.db import db_settings
from joystick_diagrams.render.theme import (
    ORIGINAL_THEME_NAME,
    TEMPLATE_ORIGINAL_THEME_ID,
)
from joystick_diagrams.ui import strings_diagrams as S

_logger = logging.getLogger(__name__)

EXPORT_PATH_SETTING_KEY = workflow_settings.EXPORT_FOLDER_SETTING_KEY
EXPORT_FORMAT_SETTING_KEY = "export_format"
EXPORT_FORMATS = ("SVG", "PNG", "PDF")
SUGGESTED_FOLDER_NAME = "Joystick Diagrams"
LINK_BUTTON_STYLE = (
    "QPushButton { color: #8AB4F8; border: none; background: transparent; "
    "padding: 0 2px; font-weight: normal; text-transform: none; } "
    "QPushButton:hover { text-decoration: underline; } "
    "QPushButton:disabled { color: #6B7280; }"
)


def link_button(text: str, tooltip: str | None = None) -> QPushButton:
    """A text button styled as a link (glossary "Change…", "Why?", "Open folder")."""
    button = QPushButton(text)
    button.setFlat(True)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setStyleSheet(LINK_BUTTON_STYLE)
    if tooltip:
        button.setToolTip(tooltip)
    return button


def suggested_export_folder() -> Path:
    """Where the first folder dialog starts: Documents on Windows, home elsewhere."""
    if sys.platform.startswith("win"):
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
    else:
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.HomeLocation
        )
    return Path(base or Path.home()) / SUGGESTED_FOLDER_NAME


def _existing_start(start: Path) -> Path:
    """``start`` or its nearest existing parent (the dialog needs a real folder)."""
    current = start
    while not current.exists() and current.parent != current:
        current = current.parent
    return current


def ask_for_folder(parent: QWidget | None, start: Path | None = None) -> Path | None:
    """The system folder dialog, pre-filled; ``None`` when cancelled. Remembers the choice."""
    start = start or suggested_export_folder()
    chosen = QFileDialog.getExistingDirectory(
        parent, S.CHOOSE_FOLDER_TITLE, str(_existing_start(start))
    )
    if not chosen:
        return None
    path = Path(chosen)
    workflow_settings.set_export_folder(path)
    return path


class ExportSettings(QWidget):
    format_changed = Signal(str)
    style_change_requested = Signal()
    folder_changed = Signal()
    other_apps_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 4, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        def heading(text: str) -> QLabel:
            label = QLabel(text)
            label.setStyleSheet("font-weight: bold;")
            return label

        # Format
        grid.addWidget(heading(S.FORMAT), 0, 0)
        self.export_format = QComboBox()
        self.export_format.setProperty("class", "view-binds-list")
        self.export_format.setAccessibleName(S.FORMAT)
        for fmt in EXPORT_FORMATS:
            self.export_format.addItem(fmt, fmt)
        saved = (db_settings.get_setting(EXPORT_FORMAT_SETTING_KEY) or "SVG").upper()
        index = self.export_format.findData(saved)
        self.export_format.setCurrentIndex(max(index, 0))
        self.export_format.currentIndexChanged.connect(self._on_format_changed)
        grid.addWidget(self.export_format, 0, 1, alignment=Qt.AlignmentFlag.AlignLeft)

        # Style
        grid.addWidget(heading(S.STYLE), 0, 2)
        style_row = QHBoxLayout()
        style_row.setSpacing(4)
        self.style_label = QLabel(ORIGINAL_THEME_NAME)
        style_row.addWidget(self.style_label)
        style_row.addWidget(QLabel("·"))
        self.change_style_button = link_button(S.CHANGE_ELLIPSIS)
        self.change_style_button.setAccessibleName(f"{S.STYLE}: {S.CHANGE_ELLIPSIS}")
        self.change_style_button.clicked.connect(self.style_change_requested.emit)
        style_row.addWidget(self.change_style_button)
        style_row.addStretch(1)
        grid.addLayout(style_row, 0, 3)

        # Save to
        grid.addWidget(heading(S.SAVE_TO), 1, 0)
        folder_row = QHBoxLayout()
        folder_row.setSpacing(4)
        self.folder_label = QLabel(S.SAVE_TO_UNSET)
        self.folder_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        folder_row.addWidget(self.folder_label)
        self.folder_separator = QLabel("·")
        folder_row.addWidget(self.folder_separator)
        self.change_folder_button = link_button(S.CHANGE_ELLIPSIS)
        self.change_folder_button.setAccessibleName(f"{S.SAVE_TO}: {S.CHANGE_ELLIPSIS}")
        self.change_folder_button.clicked.connect(self.choose_folder)
        folder_row.addWidget(self.change_folder_button)
        folder_row.addStretch(1)
        grid.addLayout(folder_row, 1, 1)

        # Also send to
        grid.addWidget(heading(S.ALSO_SEND_TO), 1, 2)
        apps_row = QHBoxLayout()
        apps_row.setSpacing(4)
        self.apps_label = QLabel(S.ALSO_SEND_NONE)
        apps_row.addWidget(self.apps_label)
        apps_row.addWidget(QLabel("·"))
        self.change_apps_button = link_button(S.CHANGE_ELLIPSIS)
        self.change_apps_button.setAccessibleName(
            f"{S.ALSO_SEND_TO}: {S.CHANGE_ELLIPSIS}"
        )
        self.change_apps_button.clicked.connect(self.other_apps_requested.emit)
        apps_row.addWidget(self.change_apps_button)
        apps_row.addStretch(1)
        grid.addLayout(apps_row, 1, 3)

        self.folder_hint = QLabel(S.SAVE_TO_HINT)
        self.folder_hint.setObjectName("device_help_label")
        self.folder_hint.setWordWrap(True)
        grid.addWidget(self.folder_hint, 2, 1, 1, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        self.refresh()

    # ── State ──

    def refresh(self) -> None:
        self.refresh_style()
        self.refresh_folder()
        self.refresh_other_apps()

    @staticmethod
    def _app_state():
        from joystick_diagrams.app_state import AppState

        return AppState() if AppState._inst is not None else None

    def _theme_service(self):
        state = self._app_state()
        return getattr(state, "theme_service", None) if state is not None else None

    def refresh_style(self) -> None:
        self.style_label.setText(self.get_style_name())

    # Older name
    refresh_style_combo = refresh_style

    def get_style_id(self) -> str:
        service = self._theme_service()
        if service is None:
            return TEMPLATE_ORIGINAL_THEME_ID
        try:
            return service.active_theme_id()
        except Exception:  # noqa: BLE001
            return TEMPLATE_ORIGINAL_THEME_ID

    def get_style_name(self) -> str:
        service = self._theme_service()
        active = self.get_style_id()
        if service is None or active == TEMPLATE_ORIGINAL_THEME_ID:
            return ORIGINAL_THEME_NAME
        for theme in service.all_themes():
            if theme.theme_id == active:
                return theme.name
        return ORIGINAL_THEME_NAME

    def refresh_folder(self) -> None:
        folder = workflow_settings.get_export_folder()
        if folder is None:
            self.folder_label.setText(S.SAVE_TO_UNSET)
            self.folder_separator.hide()
            self.change_folder_button.hide()
            self.folder_hint.hide()
        else:
            self.folder_label.setText(str(folder))
            self.folder_separator.show()
            self.change_folder_button.show()
            self.folder_hint.show()

    @property
    def export_location(self) -> str | None:
        folder = workflow_settings.get_export_folder()
        return str(folder) if folder is not None else None

    def refresh_other_apps(self) -> None:
        state = self._app_state()
        manager = getattr(state, "output_plugin_manager", None) if state else None
        wrappers = []
        if manager is not None:
            try:
                wrappers = list(manager.get_enabled_plugin_wrappers())
            except Exception as error:  # noqa: BLE001
                _logger.debug(f"Could not list other apps: {error}")
        if not wrappers:
            self.apps_label.setText(S.ALSO_SEND_NONE)
            return
        parts = [
            (S.APP_ON if getattr(w, "ready", True) else S.APP_NEEDS_SETUP).format(
                name=w.name
            )
            for w in wrappers
        ]
        self.apps_label.setText(", ".join(parts))

    def get_export_format(self) -> str:
        return self.export_format.currentData() or "SVG"

    def set_export_format(self, fmt: str) -> None:
        index = self.export_format.findData(fmt.upper())
        if index >= 0:
            self.export_format.setCurrentIndex(index)

    def _on_format_changed(self, _index: int) -> None:
        fmt = self.export_format.currentData()
        if fmt:
            db_settings.add_update_setting_value(EXPORT_FORMAT_SETTING_KEY, fmt)
            self.format_changed.emit(fmt)

    def choose_folder(self) -> Path | None:
        """Save to › Change…: the folder dialog, starting at the current folder."""
        current = workflow_settings.get_export_folder()
        start = current
        if start is None:
            raw = workflow_settings.get_export_folder_raw()
            start = Path(raw) if raw else None
        chosen = ask_for_folder(self, start)
        if chosen is not None:
            self.refresh_folder()
            self.folder_changed.emit()
        return chosen

    def set_locked(self, locked: bool) -> None:
        for widget in (
            self.export_format,
            self.change_folder_button,
            self.change_style_button,
            self.change_apps_button,
        ):
            widget.setEnabled(not locked)


if __name__ == "__main__":
    pass
