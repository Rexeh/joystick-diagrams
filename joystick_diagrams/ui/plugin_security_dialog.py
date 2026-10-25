"""The check shown before a community game (or other app) is added.

Verified games and apps are added without a dialog. Anything else needs the
player to tick "I trust where … came from" before "Add …" is enabled; the
risk is stated plainly (``docs/superpowers/specs/2026-10-25-ux-language.md``).
"""

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.ui import strings_setup as S


class PluginSecurityWarningDialog(QDialog):
    """``PluginSecurityWarningDialog(name, parent, for_app=False)``: accepted only
    after the trust box is ticked and "Add <name>" pressed."""

    def __init__(
        self, plugin_name: str, parent: QWidget | None = None, for_app: bool = False
    ):
        super().__init__(parent)
        self.setWindowTitle(S.COMMUNITY_TITLE_APP if for_app else S.COMMUNITY_TITLE)
        self.setMinimumWidth(480)
        self.setModal(True)
        self._build_ui(plugin_name, for_app)

    def _build_ui(self, plugin_name: str, for_app: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        icon_label = QLabel()
        icon_label.setPixmap(
            qta.icon("fa5s.exclamation-triangle", color="#F59E0B").pixmap(32, 32)
        )
        icon_label.setFixedSize(32, 32)
        title_row.addWidget(icon_label)
        title = QLabel(S.COMMUNITY_HEADING.format(name=plugin_name))
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #E8EAED;")
        title_row.addWidget(title, stretch=1)
        layout.addLayout(title_row)

        body = QLabel(
            (S.COMMUNITY_BODY_APP if for_app else S.COMMUNITY_BODY).format(
                name=plugin_name
            )
        )
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.PlainText)
        body.setStyleSheet("color: #E8EAED;")
        layout.addWidget(body)

        self._acknowledge_check = QCheckBox(S.COMMUNITY_TRUST.format(name=plugin_name))
        self._acknowledge_check.setStyleSheet("color: #E8EAED;")
        self._acknowledge_check.toggled.connect(self._on_acknowledge_toggled)
        layout.addWidget(self._acknowledge_check)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addStretch(1)
        cancel_btn = QPushButton(S.CANCEL)
        cancel_btn.setProperty("class", "plugin-setup-button")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setDefault(True)
        button_row.addWidget(cancel_btn)
        self._install_btn = QPushButton(S.COMMUNITY_ADD.format(name=plugin_name))
        self._install_btn.setProperty("class", "plugin-setup-button")
        self._install_btn.setEnabled(False)
        self._install_btn.setStyleSheet("QPushButton:disabled { color: #6B7280; }")
        self._install_btn.clicked.connect(self.accept)
        button_row.addWidget(self._install_btn)
        layout.addLayout(button_row)

    def _on_acknowledge_toggled(self, checked: bool):
        self._install_btn.setEnabled(checked)
