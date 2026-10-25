"""One stage tab of the four-stage strip and the chevron between two tabs.

``StageTab`` draws an 18px icon, the stage title (11px, bold, upper case) and a
status line whose icon *shape* carries the state: check-circle (ok, #34D399),
exclamation-triangle (warning, #F59E0B), times-circle (error, #F87171), a
spinning sync (busy, #4C8BF5) or nothing. The state is also exposed as the
dynamic property ``state`` ("ok" | "warning" | "error" | "busy" | "none") and
the active tab as ``active`` for QSS. The active tab is #2F6FDB with white text;
tabs are never disabled or locked.

``StageChevron`` is the "›" between tabs: grey, or #34D399 once the stage before
it is done.
"""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from joystick_diagrams.ui.stage_contract import StageStatus

COLOUR_OK = "#34D399"
COLOUR_WARNING = "#F59E0B"
COLOUR_ERROR = "#F87171"
COLOUR_BUSY = "#4C8BF5"
COLOUR_ACTIVE = "#2F6FDB"
COLOUR_MUTED = "#9AA0A6"
COLOUR_TEXT = "#E8EAED"
COLOUR_BORDER = "#3C4043"
COLOUR_CHEVRON_IDLE = "#3C4043"

STATUS_ICONS: dict[str, tuple[str | None, str]] = {
    "ok": ("fa5s.check-circle", COLOUR_OK),
    "warning": ("fa5s.exclamation-triangle", COLOUR_WARNING),
    "error": ("fa5s.times-circle", COLOUR_ERROR),
    "busy": ("fa5s.sync", COLOUR_BUSY),
    "none": (None, COLOUR_MUTED),
}

ICON_SIZE = QSize(18, 18)
STATUS_ICON_SIZE = QSize(12, 12)

_TAB_QSS = f"""
StageTab {{
    background: #252830;
    border: 1px solid {COLOUR_BORDER};
    border-radius: 8px;
}}
StageTab:hover {{
    border-color: #5F6368;
}}
StageTab[active="true"] {{
    background: {COLOUR_ACTIVE};
    border-color: {COLOUR_ACTIVE};
}}
StageTab:focus {{
    border: 2px solid {COLOUR_BUSY};
}}
StageTab QLabel {{
    background: transparent;
}}
StageTab QLabel#stageTitle {{
    color: {COLOUR_MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
StageTab QLabel#stageStatus {{
    color: {COLOUR_MUTED};
    font-size: 11px;
}}
StageTab[state="warning"] QLabel#stageStatus {{ color: {COLOUR_WARNING}; }}
StageTab[state="error"] QLabel#stageStatus {{ color: {COLOUR_ERROR}; }}
StageTab[active="true"] QLabel#stageTitle,
StageTab[active="true"] QLabel#stageStatus {{ color: #ffffff; }}
"""


class StageTab(QFrame):
    """A clickable, focusable stage tab. ``clicked`` carries the stage index."""

    clicked = Signal(int)

    def __init__(
        self,
        index: int,
        title: str,
        icon_name: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.index = index
        self.title = title
        self._icon_name = icon_name
        self._status = StageStatus()
        self._active = False
        self._spin: qta.Spin | None = None

        self.setObjectName(f"stageTab{index}")
        self.setProperty("state", "none")
        self.setProperty("active", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumWidth(184)
        self.setFixedHeight(56)
        self.setStyleSheet(_TAB_QSS)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 0, 14, 0)
        root.setSpacing(10)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(ICON_SIZE)
        root.addWidget(self.icon_label)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(3)

        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("stageTitle")
        text.addWidget(self.title_label)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(5)
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(STATUS_ICON_SIZE)
        self.status_icon.hide()
        status_row.addWidget(self.status_icon)
        self.status_label = QLabel("")
        self.status_label.setObjectName("stageStatus")
        status_row.addWidget(self.status_label, 1)
        text.addLayout(status_row)

        root.addLayout(text, 1)
        self._paint_icon()
        self._update_accessible_name()

    # ── State ──

    @property
    def status(self) -> StageStatus:
        return self._status

    @property
    def state(self) -> str:
        return str(self.property("state"))

    def set_status(self, status: StageStatus) -> None:
        self._status = status
        icon = status.icon if status.icon in STATUS_ICONS else "none"
        self.setProperty("state", icon)
        self.status_label.setText(status.text)
        self._paint_status_icon()
        self._repolish()
        self._update_accessible_name()

    def set_active(self, active: bool) -> None:
        if self._active == active:
            return
        self._active = active
        self.setProperty("active", "true" if active else "false")
        self._paint_icon()
        self._paint_status_icon()
        self._repolish()

    @property
    def is_active(self) -> bool:
        return self._active

    # ── Painting ──

    def _paint_icon(self) -> None:
        colour = "#ffffff" if self._active else COLOUR_MUTED
        self.icon_label.setPixmap(
            qta.icon(self._icon_name, color=colour).pixmap(ICON_SIZE)
        )

    def _paint_status_icon(self) -> None:
        name, colour = STATUS_ICONS.get(self.state, STATUS_ICONS["none"])
        if self._spin is not None:
            self._spin.stop()
            self._spin = None
        if name is None:
            self.status_icon.clear()
            self.status_icon.hide()
            return
        if self._active:
            colour = "#ffffff"
        if self.state == "busy":
            self._spin = qta.Spin(self.status_icon, interval=12, step=6)
            icon = qta.icon(name, color=colour, animation=self._spin)
        else:
            icon = qta.icon(name, color=colour)
        self.status_icon.setPixmap(icon.pixmap(STATUS_ICON_SIZE))
        self.status_icon.show()

    def _repolish(self) -> None:
        for widget in (self, self.title_label, self.status_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self.update()

    def _update_accessible_name(self) -> None:
        text = self._status.text
        self.setAccessibleName(f"{self.title}, {text}" if text else self.title)

    # ── Interaction ──

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self.index)
            return
        super().keyPressEvent(event)


class StageChevron(QLabel):
    """The "›" between two stage tabs; green once the stage before it is done."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._done = False
        self.setFixedSize(16, 16)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: transparent;")
        self.set_done(False)

    @property
    def is_done(self) -> bool:
        return self._done

    def set_done(self, done: bool) -> None:
        self._done = done
        colour = COLOUR_OK if done else COLOUR_CHEVRON_IDLE
        self.setPixmap(
            qta.icon("fa5s.chevron-right", color=colour).pixmap(QSize(14, 14))
        )
        self.setProperty("class", "nav-chevron completed" if done else "nav-chevron")


if __name__ == "__main__":
    pass
