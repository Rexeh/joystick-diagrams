"""Reusable section header widget with icon, title, subtitle, and optional action area."""

import qtawesome as qta
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class SectionHeader(QWidget):
    """Page/section header with icon, title, optional subtitle, and right-side action area.

    Usage:
        header = SectionHeader("fa5s.cog", "Plugin Setup", "Enable and configure your plugins")
        header.add_action(some_button)
        layout.addWidget(header)
    """

    def __init__(
        self,
        icon_name: str,
        title: str,
        subtitle: str | None = None,
        icon_color: str = "#4C8BF5",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setProperty("class", "section-header")
        self.setFixedHeight(60)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 8)
        root.setSpacing(12)

        # Icon
        icon_label = QLabel()
        icon = qta.icon(icon_name, color=icon_color)
        icon_label.setPixmap(icon.pixmap(QSize(28, 28)))
        icon_label.setFixedSize(28, 28)
        root.addWidget(icon_label)

        # Title + subtitle
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        title_label = QLabel(title)
        title_label.setProperty("class", "section-header-title")
        text_col.addWidget(title_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setProperty("class", "section-header-subtitle")
            text_col.addWidget(sub_label)

        root.addLayout(text_col, stretch=1)

        # Right-side action area
        self._action_layout = QHBoxLayout()
        self._action_layout.setContentsMargins(0, 0, 0, 0)
        self._action_layout.setSpacing(8)
        root.addLayout(self._action_layout)

    def add_action(self, widget: QWidget) -> None:
        """Add a widget (button, label, etc.) to the right-side action area."""
        self._action_layout.addWidget(widget)
