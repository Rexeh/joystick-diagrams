"""Reusable plugin card widget for both parser and output plugins in the Settings page.

Compact single-row design matching the Setup page's PluginCard pattern:
[icon] [name+version / status+trust] <stretch> [enabled] [update] [uninstall]
"""

import qtawesome as qta
from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

# Trust status constants
TRUST_BUNDLED = "bundled"
TRUST_SIGNED = "signed"
TRUST_USER_ACCEPTED = "trusted"
TRUST_UNTRUSTED = "untrusted"

_TRUST_BADGE = {
    TRUST_BUNDLED: ("fa5s.cube", "#9AA0A6", "Bundled plugin"),
    TRUST_SIGNED: ("fa5s.shield-alt", "#34D399", "Signed by developer"),
    TRUST_USER_ACCEPTED: ("fa5s.shield-alt", "#F59E0B", "Trusted by user"),
    TRUST_UNTRUSTED: ("fa5s.shield-alt", "#EF4444", "Untrusted"),
}


class PluginCard(QFrame):
    """A compact card showing a single plugin in a single row.

    Works for both PluginWrapper and OutputPluginWrapper since they share
    the same interface: .name, .version, .icon, .enabled, .ready, .has_settings()
    """

    uninstall_requested = Signal(str)
    config_requested = Signal(object)

    def __init__(
        self,
        wrapper,
        is_user_plugin: bool = False,
        trust_status: str = TRUST_BUNDLED,
        parent=None,
    ):
        super().__init__(parent)
        self._wrapper = wrapper
        self._is_user_plugin = is_user_plugin
        self._trust_status = trust_status
        self._build_ui()
        self.refresh_status()

    def _build_ui(self):
        self.setProperty("class", "plugin-card")
        self.setMinimumHeight(54)
        self.setMaximumHeight(70)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(12)

        # Left: plugin icon
        icon_label = QLabel()
        icon_label.setPixmap(QIcon(self._wrapper.icon).pixmap(QSize(24, 24)))
        icon_label.setFixedSize(24, 24)
        icon_label.setStyleSheet("background: transparent;")
        root.addWidget(icon_label)

        # Center: two-line text block (name+version / status+trust)
        center = QVBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(2)

        # Line 1: name + version + user badge
        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        name_label = QLabel(self._wrapper.name)
        name_label.setProperty("class", "plugin-card-name")
        name_row.addWidget(name_label)

        version_label = QLabel(f"v{self._wrapper.version}")
        version_label.setProperty("class", "plugin-card-version")
        name_row.addWidget(version_label)

        if self._is_user_plugin:
            badge = QLabel("User")
            badge.setStyleSheet(
                "color: #F59E0B; background: rgba(245, 158, 11, 0.15); "
                "border-radius: 3px; padding: 1px 6px; font-size: 10px;"
            )
            badge.setFixedHeight(16)
            name_row.addWidget(badge)

        name_row.addStretch()
        center.addLayout(name_row)

        # Line 2: status icon + status text + trust badge
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(5)

        self._status_icon = QLabel()
        self._status_icon.setFixedSize(12, 12)
        self._status_icon.setStyleSheet("background: transparent;")
        status_row.addWidget(self._status_icon)

        self._status_label = QLabel()
        self._status_label.setProperty("class", "plugin-card-status")
        status_row.addWidget(self._status_label)

        # Trust badge (small inline icon)
        badge_icon, badge_color, badge_tooltip = _TRUST_BADGE.get(
            self._trust_status, _TRUST_BADGE[TRUST_UNTRUSTED]
        )
        trust_label = QLabel()
        trust_label.setPixmap(
            qta.icon(badge_icon, color=badge_color).pixmap(QSize(12, 12))
        )
        trust_label.setFixedSize(12, 12)
        trust_label.setToolTip(badge_tooltip)
        trust_label.setStyleSheet("background: transparent;")
        status_row.addWidget(trust_label)

        status_row.addStretch()
        center.addLayout(status_row)

        root.addLayout(center, stretch=1)

        # Right: action buttons
        right = QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(8)

        # Enable/disable toggle
        self._enable_btn = QPushButton(
            "Enabled" if self._wrapper.enabled else "Disabled"
        )
        self._enable_btn.setCheckable(True)
        self._enable_btn.setChecked(self._wrapper.enabled)
        self._enable_btn.setProperty("class", "enabled-button")
        self._enable_btn.clicked.connect(self._toggle_enabled)
        right.addWidget(self._enable_btn)

        # Setup/Update button
        if self._wrapper.has_settings():
            self._setup_btn = QPushButton()
            self._setup_btn.setProperty("class", "plugin-setup-button")
            self._setup_btn.clicked.connect(
                lambda: self.config_requested.emit(self._wrapper)
            )
            right.addWidget(self._setup_btn)
        else:
            self._setup_btn = None

        # Uninstall button (user plugins only)
        if self._is_user_plugin:
            uninstall_btn = QPushButton()
            uninstall_btn.setIcon(qta.icon("fa5s.trash-alt", color="#EF4444"))
            uninstall_btn.setIconSize(QSize(14, 14))
            uninstall_btn.setToolTip(f"Uninstall {self._wrapper.name}")
            uninstall_btn.setFixedSize(QSize(28, 28))
            uninstall_btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; }"
                "QPushButton:hover { background: rgba(239, 68, 68, 0.15); border-radius: 4px; }"
            )
            uninstall_btn.clicked.connect(
                lambda: self.uninstall_requested.emit(self._wrapper.name)
            )
            right.addWidget(uninstall_btn)

        root.addLayout(right)

    def refresh_status(self):
        """Update the status indicator and card accent based on current plugin state."""
        if self._wrapper.ready:
            self._set_status("ready", "Ready", "fa5s.check-circle", "#34D399")
            self._update_card_class("ready")
        else:
            self._set_status(
                "not-ready", "Not configured", "fa5s.exclamation-circle", "#F59E0B"
            )
            self._update_card_class("not-ready")

        if self._setup_btn:
            self._setup_btn.setText("Update" if self._wrapper.ready else "Setup")

    def _set_status(self, css_class: str, text: str, icon_name: str, color: str):
        self._status_icon.setPixmap(
            qta.icon(icon_name, color=color).pixmap(QSize(12, 12))
        )
        self._status_label.setText(text)
        self._status_label.setProperty("class", f"plugin-card-status {css_class}")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _update_card_class(self, state: str):
        self.setProperty("class", f"plugin-card {state}")
        self.style().unpolish(self)
        self.style().polish(self)

    def _toggle_enabled(self, checked: bool):
        self._wrapper.enabled = checked
        self._enable_btn.setText("Enabled" if checked else "Disabled")
