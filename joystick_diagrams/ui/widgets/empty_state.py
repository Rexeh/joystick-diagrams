"""Generic empty state: an icon, a message and an optional action button.

Styled like ``PluginEmptyState`` but without any catalog logic, for screens that
need "nothing here yet, do X" (Appearance preview, Layout). Deliberately added
because the app had no reusable empty-state widget (plan §5.5.1).
"""

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class EmptyState(QWidget):
    action_requested = Signal()

    def __init__(
        self,
        message: str,
        icon_name: str = "fa5s.image",
        action_text: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(12)
        root.addStretch(1)

        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color="#4C8BF5").pixmap(QSize(40, 40)))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(icon)

        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("color: #9AA0A6; font-size: 12px;")
        root.addWidget(self.message_label)

        self.action_button: QPushButton | None = None
        if action_text:
            self.action_button = QPushButton(action_text)
            self.action_button.setProperty("class", "plugin-setup-button")
            self.action_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.action_button.clicked.connect(self.action_requested.emit)
            root.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignCenter)

        root.addStretch(2)

    def set_message(self, text: str) -> None:
        self.message_label.setText(text)
