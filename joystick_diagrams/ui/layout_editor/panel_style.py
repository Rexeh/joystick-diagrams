"""Shared look of the Layout screen's right-hand panels and toolbar (the
controller panel in ``customise_layout`` and the page panel in
``layout_page_panel``): colours, label helpers and button styles."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QToolButton

HELP_STYLE = "color: #9AA0A6; font-size: 12px; background: transparent;"
HEADING_STYLE = (
    "color: #E8EAED; font-size: 14px; font-weight: bold; background: transparent;"
)
LABEL_STYLE = "color: #E8EAED; font-size: 12px; background: transparent;"
MUTED_STYLE = "color: #9AA0A6; font-size: 11px; background: transparent;"
PROFILE_STYLE = "color: #F59E0B; font-size: 11px; background: transparent;"
TOOL_STYLE = """
QToolButton {
    background: #2c2f38; color: #E8EAED; border: 1px solid #3C4043; border-radius: 4px;
    margin: 0px; padding: 4px 10px; min-height: 24px;
}
QToolButton:hover { background: #3C4043; border-color: #5F6368; }
QToolButton:pressed, QToolButton:checked { background: #2F6FDB; border-color: #2F6FDB; color: white; }
QToolButton:disabled { color: #5F6368; border-color: #2c2f38; }
QToolButton::menu-indicator { subcontrol-position: right center; subcontrol-origin: padding; left: -2px; }
"""
PANEL_BUTTON_STYLE = """
QPushButton {
    background: #2c2f38; color: #E8EAED; border: 1px solid #3C4043; border-radius: 4px;
    padding: 4px 10px; min-height: 22px; text-align: left;
}
QPushButton:hover { background: #3C4043; border-color: #5F6368; }
QPushButton:disabled { color: #5F6368; border-color: #2c2f38; }
"""
NOTICE_STYLE = (
    "QFrame#notice_frame { background: #2c2f38; border: 1px solid #3C4043; "
    "border-radius: 6px; }"
)


def help_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(HELP_STYLE)
    return label


def heading_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(HEADING_STYLE)
    return label


def tool_button(text: str, tooltip: str, icon: str | None = None) -> QToolButton:
    button = QToolButton()
    button.setText(text)
    button.setToolTip(tooltip)
    button.setAccessibleName(text)
    button.setStyleSheet(TOOL_STYLE)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon:
        button.setIcon(qta.icon(icon, color="#E8EAED"))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    return button


def panel_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setStyleSheet(PANEL_BUTTON_STYLE)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


if __name__ == "__main__":
    pass
