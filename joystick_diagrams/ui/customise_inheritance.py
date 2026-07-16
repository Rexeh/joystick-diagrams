import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.ui import parent_profiles

_logger = logging.getLogger(__name__)


class CustomiseInheritance(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.appState = AppState()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Help text explaining inheritance
        help_text = QLabel(
            "Feed profiles into another profile, to combine the binds into one. "
            '<a href="https://joystick-diagrams.com/setup/profile-chaining/">Learn more</a>'
        )
        help_text.setObjectName("device_help_label")
        help_text.setTextFormat(Qt.TextFormat.RichText)
        help_text.setOpenExternalLinks(True)
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # Profile selector row
        selector_row = QHBoxLayout()
        selector_row.setSpacing(8)

        selector_label = QLabel("Profile:")
        selector_label.setStyleSheet("font-weight: bold;")
        selector_row.addWidget(selector_label)

        self.profile_combo = QComboBox()
        self.profile_combo.setMaxVisibleItems(15)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        selector_row.addWidget(self.profile_combo, stretch=1)

        layout.addLayout(selector_row)

        # The existing parent_profile_ui widget
        self.parent_widget = parent_profiles.parent_profile_ui()
        layout.addWidget(self.parent_widget)

        layout.addStretch()

    def refresh(self):
        """Rebuild the profile selector from current app state."""
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()

        for wrapper in self.appState.profile_wrappers:
            self.profile_combo.addItem(
                QIcon(wrapper.profile_origin.icon),
                wrapper.profile_name,
                wrapper,
            )

        self.profile_combo.blockSignals(False)

        if self.profile_combo.count() > 0:
            self.profile_combo.setCurrentIndex(0)
            self._on_profile_changed(0)

    def _on_profile_changed(self, index: int):
        wrapper = self.profile_combo.currentData(Qt.ItemDataRole.UserRole)
        if wrapper:
            self.parent_widget.set_profile_parent_map(wrapper)


if __name__ == "__main__":
    pass
