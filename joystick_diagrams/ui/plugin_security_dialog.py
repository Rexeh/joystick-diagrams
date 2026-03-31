"""Security warning dialogs for plugin installation."""

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class PluginSecurityWarningDialog(QDialog):
    """Shown when installing an unsigned/untrusted plugin.

    Requires the user to acknowledge the risk via a checkbox before
    the Install button becomes enabled.
    """

    def __init__(self, plugin_name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Security Warning - Untrusted Plugin")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._build_ui(plugin_name)

    def _build_ui(self, plugin_name: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Warning icon + title row
        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(
            qta.icon("fa5s.exclamation-triangle", color="#F59E0B").pixmap(32, 32)
        )
        icon_label.setFixedSize(32, 32)
        title_row.addWidget(icon_label)

        title = QLabel("Untrusted Plugin")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #E8EAED;")
        title_row.addWidget(title, stretch=1)

        layout.addLayout(title_row)

        # Warning body
        body = QLabel(
            f"You are about to install <b>'{plugin_name}'</b>.<br><br>"
            "This plugin is <b>not signed</b> by the Joystick Diagrams developer "
            "and has not been verified.<br><br>"
            "Plugins can execute code with your user account's permissions and could:"
            "<ul>"
            "<li>Access, modify, or delete your files</li>"
            "<li>Connect to the internet</li>"
            "<li>Modify system settings</li>"
            "</ul>"
            "<b>Only install plugins from sources you trust.</b>"
        )
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setStyleSheet("color: #E8EAED; line-height: 1.4;")
        layout.addWidget(body)

        # Acknowledgement checkbox
        self._acknowledge_check = QCheckBox(
            "I understand the risks and trust this plugin"
        )
        self._acknowledge_check.setStyleSheet("color: #9AA0A6;")
        self._acknowledge_check.toggled.connect(self._on_acknowledge_toggled)
        layout.addWidget(self._acknowledge_check)

        # Button row
        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "plugin-setup-button")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setDefault(True)
        button_row.addWidget(cancel_btn)

        self._install_btn = QPushButton("Install Anyway")
        self._install_btn.setProperty("class", "plugin-setup-button")
        self._install_btn.setEnabled(False)
        self._install_btn.setStyleSheet("QPushButton:disabled { color: #6B7280; }")
        self._install_btn.clicked.connect(self.accept)
        button_row.addWidget(self._install_btn)

        layout.addLayout(button_row)

    def _on_acknowledge_toggled(self, checked: bool):
        self._install_btn.setEnabled(checked)


class PluginSignedDialog(QMessageBox):
    """Informational dialog shown when installing a verified/signed plugin."""

    def __init__(self, plugin_name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Verified Plugin")
        self.setIcon(QMessageBox.Icon.Information)
        self.setIconPixmap(qta.icon("fa5s.shield-alt", color="#34D399").pixmap(48, 48))
        self.setText(
            f"<b>'{plugin_name}'</b> is signed and verified by the "
            "Joystick Diagrams developer."
        )
        self.setInformativeText("This plugin is safe to install.")
        self.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.setDefaultButton(QMessageBox.StandardButton.Ok)
        self.button(QMessageBox.StandardButton.Ok).setText("Install")
