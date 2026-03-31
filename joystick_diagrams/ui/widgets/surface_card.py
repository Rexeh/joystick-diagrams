"""Reusable surface card container that wraps content in an elevated panel."""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class SurfaceCard(QFrame):
    """A visually distinct container with a subtle border and elevated background.

    Usage:
        card = SurfaceCard("Plugins", parent=self)
        card.content_layout.addWidget(my_tree_widget)
        page_layout.addWidget(card)
    """

    def __init__(
        self,
        title: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setProperty("class", "surface-card")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)

        if title:
            title_label = QLabel(title)
            title_label.setProperty("class", "surface-card-title")
            outer.addWidget(title_label)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        outer.addLayout(self.content_layout)
