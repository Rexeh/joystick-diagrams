"""Drag-and-drop widget for plugin ZIP file installation."""

from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

_STYLE_DEFAULT = (
    "border: 2px dashed #3C4043; border-radius: 8px; "
    "padding: 16px; background: #252830;"
)
_STYLE_HOVER = (
    "border: 2px dashed #4C8BF5; border-radius: 8px; "
    "padding: 16px; background: #2c2f38;"
)

_STYLE_COMPACT_DEFAULT = (
    "border: 1px dashed #3C4043; border-radius: 4px; "
    "padding: 4px 12px; background: #252830;"
)
_STYLE_COMPACT_HOVER = (
    "border: 1px dashed #4C8BF5; border-radius: 4px; "
    "padding: 4px 12px; background: #2c2f38;"
)


class DropZoneWidget(QWidget):
    """A drop target that accepts .zip files and directories.

    Emits file_dropped(Path) when a valid file/folder is dropped.
    Use compact=True for an inline variant that fits inside a button row.
    """

    file_dropped = Signal(Path)

    def __init__(
        self,
        label_text: str = "Drag & drop a plugin ZIP here",
        parent=None,
        compact: bool = False,
    ):
        super().__init__(parent)
        self._compact = compact
        self.setAcceptDrops(True)

        if compact:
            self._style_default = _STYLE_COMPACT_DEFAULT
            self._style_hover = _STYLE_COMPACT_HOVER
            self.setMinimumHeight(36)
            self.setMaximumHeight(36)
            icon_size = 14
            margins = (8, 2, 8, 2)
        else:
            self._style_default = _STYLE_DEFAULT
            self._style_hover = _STYLE_HOVER
            self.setMinimumHeight(60)
            icon_size = 20
            margins = (12, 8, 12, 8)

        self.setStyleSheet(self._style_default)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(*margins)
        layout.setSpacing(6 if compact else 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel()
        icon_label.setPixmap(
            qta.icon("fa5s.file-archive", color="#9AA0A6").pixmap(
                QSize(icon_size, icon_size)
            )
        )
        icon_label.setFixedSize(icon_size, icon_size)
        icon_label.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon_label)

        text_label = QLabel(label_text)
        text_label.setStyleSheet(
            "color: #9AA0A6; border: none; background: transparent;"
            + (" font-size: 11px;" if compact else "")
        )
        layout.addWidget(text_label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(
                u.toLocalFile().endswith(".zip") or Path(u.toLocalFile()).is_dir()
                for u in urls
            ):
                event.acceptProposedAction()
                self.setStyleSheet(self._style_hover)
                return
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self.setStyleSheet(self._style_default)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(self._style_default)
        urls = event.mimeData().urls()
        for url in urls:
            local_path = Path(url.toLocalFile())
            if local_path.suffix == ".zip" and local_path.is_file():
                self.file_dropped.emit(local_path)
                return
            if local_path.is_dir():
                self.file_dropped.emit(local_path)
                return
