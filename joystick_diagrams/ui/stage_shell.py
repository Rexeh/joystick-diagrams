"""Building blocks of the four-stage shell used by ``ui/main_window.py``.

- ``StageStrip``: the four ``StageTab``s with chevrons and the settings cog.
- ``BannerSlot``: the reserved notice slot under the strip (``show_banner`` /
  ``clear_banner``); several notices stack, each with its own Dismiss.
- ``StageFooter``: the pinned footer: hint and secondary action at the left, one
  44px primary at the right (``set_actions``).
- ``ReadPopover``: the small window under the 1. Setup tab while the games are
  read again ("what is kept", Read again, Turn off automatic reading).
- ``GameReader``: runs ``PluginExecutor`` on the thread pool and turns the
  result into a ``ReadOutcome`` (profiles reprocessed, inventory recorded).
- ``PlaceholderStagePage``: stands in for stage 3 / 4 when F3's pages are not
  importable, so the app still starts.
- Small settings helpers: first-run flag, dismissed "new controller" notices,
  the upgrade notice flag.

Everything here is UI-thread code except ``PluginExecutor.run``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any

import qtawesome as qta
from PySide6.QtCore import (
    QObject,
    QPoint,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.db import db_settings
from joystick_diagrams.plugin_wrapper import PluginWrapper
from joystick_diagrams.ui import strings_shell as S
from joystick_diagrams.ui.stage_contract import (
    STAGE_BINDINGS,
    STAGE_CONTROLLERS,
    STAGE_COUNT,
    STAGE_DIAGRAMS,
    STAGE_SETUP,
    STAGE_TITLES,
    NextAction,
    ReadOutcome,
    StageStatus,
)
from joystick_diagrams.ui.widgets.empty_state import EmptyState
from joystick_diagrams.ui.widgets.stage_tab import StageChevron, StageTab

_logger = logging.getLogger(__name__)

STAGE_ICONS = ("fa5s.cog", "fa5s.gamepad", "fa5s.link", "fa5s.file-export")

FIRST_RUN_DONE_KEY = "workflow_first_run_done"
NEW_CONTROLLER_DISMISSED_KEY = "new_controller_notices_dismissed"
UPGRADE_NOTICE_SHOWN_KEY = "four_stage_intro_shown"

PRIMARY_QSS = """
QPushButton#stagePrimary, QPushButton#stageSecondary { text-transform: none; }
QPushButton#stagePrimary {
    background: #2F6FDB; color: #ffffff; border: 1px solid #2F6FDB; border-radius: 6px;
    min-height: 42px; max-height: 42px; padding: 0px 24px;
    font-size: 13px; font-weight: 700;
}
QPushButton#stagePrimary:hover { background: #4C8BF5; border-color: #4C8BF5; }
QPushButton#stagePrimary:focus { border: 2px solid #4C8BF5; }
QPushButton#stagePrimary:disabled { background: #3C4043; border-color: #3C4043; color: #6B7280; }
"""
SECONDARY_QSS = """
QPushButton#stageSecondary {
    background: transparent; color: #8AB4F8; border: 1px solid transparent; border-radius: 4px;
    min-height: 32px; padding: 0px 10px; font-size: 11px; font-weight: 700;
}
QPushButton#stageSecondary:hover { background: #2c2f38; }
QPushButton#stageSecondary:disabled { color: #6B7280; }
"""
BANNER_QSS = """
QFrame#stageBanner[tone="info"] { background: rgba(76, 139, 245, 0.08); border: 1px solid rgba(76, 139, 245, 0.28); border-radius: 6px; }
QFrame#stageBanner[tone="warning"] { background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.28); border-radius: 6px; }
QFrame#stageBanner[tone="ok"] { background: rgba(52, 211, 153, 0.08); border: 1px solid rgba(52, 211, 153, 0.28); border-radius: 6px; }
QFrame#stageBanner QLabel { background: transparent; color: #E8EAED; font-size: 13px; }
QFrame#stageBanner QLabel#bannerDetail { color: #9AA0A6; font-size: 12px; }
QFrame#stageBanner QPushButton {
    text-transform: none;
    background: #2c2f38; color: #E8EAED; border: 1px solid #3C4043; border-radius: 4px;
    min-height: 30px; padding: 0px 14px; font-size: 11px; font-weight: 700;
}
QFrame#stageBanner QPushButton:hover { background: #3C4043; border-color: #4C8BF5; }
QFrame#stageBanner QToolButton { background: transparent; border: none; }
"""
POPOVER_QSS = """
QFrame#readPopover { background: #2c2f38; border: 1px solid #3C4043; border-radius: 8px; }
QFrame#readPopover QLabel { background: transparent; color: #E8EAED; font-size: 12px; }
QFrame#readPopover QLabel#popoverTitle { font-weight: 700; }
QFrame#readPopover QLabel#popoverKept { color: #9AA0A6; }
QFrame#readPopover QPushButton {
    text-transform: none;
    background: #2c2f38; color: #E8EAED; border: 1px solid #3C4043; border-radius: 4px;
    min-height: 28px; padding: 0px 12px; font-size: 11px; font-weight: 700;
}
QFrame#readPopover QPushButton:hover { background: #3C4043; border-color: #4C8BF5; }
QFrame#readPopover QPushButton:disabled { color: #6B7280; }
"""

ActionList = Iterable[tuple[str, Callable[[], None]]]


def now_time_text(now: datetime | None = None) -> str:
    """ "09:41": the time shown on status lines."""
    return (now or datetime.now()).strftime("%H:%M")


# ── Settings helpers ──


def is_first_run_done() -> bool:
    return (db_settings.get_setting(FIRST_RUN_DONE_KEY) or "").strip().lower() == "true"


def mark_first_run_done() -> None:
    db_settings.add_update_setting_value(FIRST_RUN_DONE_KEY, "true")


def dismissed_new_controllers() -> set[str]:
    raw = db_settings.get_setting(NEW_CONTROLLER_DISMISSED_KEY)
    if not raw:
        return set()
    try:
        data = json.loads(raw)
    except ValueError:
        return set()
    return {str(item) for item in data} if isinstance(data, list) else set()


def dismiss_new_controller(guid: str) -> None:
    guids = dismissed_new_controllers()
    guids.add(guid)
    db_settings.add_update_setting_value(
        NEW_CONTROLLER_DISMISSED_KEY, json.dumps(sorted(guids))
    )


def upgrade_notice_shown() -> bool:
    return (
        db_settings.get_setting(UPGRADE_NOTICE_SHOWN_KEY) or ""
    ).strip().lower() == "true"


def mark_upgrade_notice_shown() -> None:
    db_settings.add_update_setting_value(UPGRADE_NOTICE_SHOWN_KEY, "true")


# ── Strip ──


class StageStrip(QWidget):
    """Four stage tabs, three chevrons and the settings cog."""

    stage_selected = Signal(int)
    settings_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.tabs: list[StageTab] = []
        self.chevrons: list[StageChevron] = []
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 0)
        root.setSpacing(0)
        for index, title in enumerate(STAGE_TITLES):
            tab = StageTab(index, title, STAGE_ICONS[index])
            tab.clicked.connect(self.stage_selected.emit)
            root.addWidget(tab)
            self.tabs.append(tab)
            if index < STAGE_COUNT - 1:
                chevron = StageChevron()
                root.addSpacing(4)
                root.addWidget(chevron)
                root.addSpacing(4)
                self.chevrons.append(chevron)
        root.addStretch(1)
        self.settings_button = QToolButton()
        self.settings_button.setIcon(qta.icon("fa5s.cog", color="#9AA0A6"))
        self.settings_button.setIconSize(QSize(18, 18))
        self.settings_button.setFixedSize(32, 32)
        self.settings_button.setToolTip(S.SETTINGS_TIP)
        self.settings_button.setAccessibleName(S.SETTINGS_TIP)
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.setAutoRaise(True)
        self.settings_button.setCheckable(True)
        self.settings_button.setObjectName("stageSettings")
        self.settings_button.setStyleSheet(
            "QToolButton#stageSettings { background: transparent; border: none;"
            " border-radius: 6px; }"
            "QToolButton#stageSettings:hover { background: #2c2f38; }"
            "QToolButton#stageSettings:checked { background: #2F6FDB; }"
            "QToolButton#stageSettings:focus { border: 2px solid #4C8BF5; }"
        )
        self.settings_button.clicked.connect(self.settings_clicked.emit)
        root.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_active(self, index: int | None) -> None:
        for tab in self.tabs:
            tab.set_active(tab.index == index)
        self.settings_button.setChecked(index is None)

    def set_statuses(self, statuses: list[StageStatus]) -> None:
        for tab, status in zip(self.tabs, statuses, strict=False):
            tab.set_status(status)
        for index, chevron in enumerate(self.chevrons):
            chevron.set_done(index < len(statuses) and statuses[index].is_done)

    def tab(self, index: int) -> StageTab:
        return self.tabs[index]


# ── Banner slot ──


class BannerSlot(QWidget):
    """The reserved notice slot: hidden when empty, one frame per notice."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 12, 20, 0)
        self._layout.setSpacing(8)
        self._banners: list[QFrame] = []
        self.setStyleSheet(BANNER_QSS)
        self.hide()

    @property
    def banners(self) -> list[QFrame]:
        return list(self._banners)

    def show_banner(
        self,
        text: str,
        actions: ActionList = (),
        tone: str = "info",
        detail: str | None = None,
        dismissible: bool = True,
        key: str | None = None,
        on_dismiss: Callable[[], None] | None = None,
    ) -> QFrame:
        """Add a notice. ``key`` replaces an existing notice with the same key."""
        if key is not None:
            for existing in list(self._banners):
                if existing.property("bannerKey") == key:
                    self.remove_banner(existing)
        frame = QFrame()
        frame.setObjectName("stageBanner")
        frame.setProperty("tone", tone)
        frame.setProperty("bannerKey", key)
        frame.setProperty("bannerText", text)
        row = QHBoxLayout(frame)
        row.setContentsMargins(14, 10, 10, 10)
        row.setSpacing(12)
        icon_name = {
            "warning": "fa5s.exclamation-triangle",
            "ok": "fa5s.check-circle",
        }.get(tone, "fa5s.info-circle")
        colour = {"warning": "#F59E0B", "ok": "#34D399"}.get(tone, "#4C8BF5")
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=colour).pixmap(QSize(16, 16)))
        icon.setFixedSize(16, 16)
        row.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        label = QLabel(text)
        label.setObjectName("bannerText")
        label.setWordWrap(True)
        text_col.addWidget(label)
        if detail:
            detail_label = QLabel(detail)
            detail_label.setObjectName("bannerDetail")
            detail_label.setWordWrap(True)
            text_col.addWidget(detail_label)
        row.addLayout(text_col, 1)
        for action_label, callback in actions:
            button = QPushButton(action_label)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            # Never hand Qt's ``checked`` to the callback (default-arg lambdas).
            button.clicked.connect(lambda _checked=False, cb=callback: cb())
            row.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
        if dismissible:
            close = QToolButton()
            close.setIcon(qta.icon("fa5s.times", color="#9AA0A6"))
            close.setIconSize(QSize(12, 12))
            close.setFixedSize(24, 24)
            close.setToolTip(S.BANNER_DISMISS)
            close.setAccessibleName(S.BANNER_DISMISS)
            close.setCursor(Qt.CursorShape.PointingHandCursor)

            def _dismiss(_checked=False, frame=frame, on_dismiss=on_dismiss):
                self.remove_banner(frame)
                if on_dismiss is not None:
                    on_dismiss()

            close.clicked.connect(_dismiss)
            row.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        self._layout.addWidget(frame)
        self._banners.append(frame)
        self.show()
        return frame

    def remove_banner(self, frame: QFrame) -> None:
        if frame in self._banners:
            self._banners.remove(frame)
            self._layout.removeWidget(frame)
            frame.hide()
            frame.deleteLater()
        if not self._banners:
            self.hide()

    def clear_banner(self, key: str | None = None) -> None:
        for frame in list(self._banners):
            if key is None or frame.property("bannerKey") == key:
                self.remove_banner(frame)

    def texts(self) -> list[str]:
        return [str(frame.property("bannerText")) for frame in self._banners]


# ── Footer ──


class StageFooter(QFrame):
    """Pinned footer: [secondary] [hint ……] [primary 44px]."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("stageFooter")
        self.setStyleSheet(
            "QFrame#stageFooter { border: none; border-top: 1px solid #3C4043;"
            " border-radius: 0px; background: #1a1d23; }"
            "QFrame#stageFooter QLabel#footerHint { color: #9AA0A6; font-size: 12px; background: transparent; }"
            + PRIMARY_QSS
            + SECONDARY_QSS
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(20, 12, 20, 12)
        row.setSpacing(12)
        self.secondary_button = QPushButton()
        self.secondary_button.setObjectName("stageSecondary")
        self.secondary_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.secondary_button.hide()
        row.addWidget(self.secondary_button)
        self.hint_label = QLabel("")
        self.hint_label.setObjectName("footerHint")
        self.hint_label.setWordWrap(True)
        self.hint_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        row.addWidget(self.hint_label, 1)
        self.primary_button = QPushButton()
        self.primary_button.setObjectName("stagePrimary")
        self.primary_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.primary_button.setFixedHeight(44)
        self.primary_button.hide()
        row.addWidget(self.primary_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self._primary: NextAction | None = None
        self._secondary: NextAction | None = None
        self.primary_button.clicked.connect(self._run_primary)
        self.secondary_button.clicked.connect(self._run_secondary)

    def set_actions(
        self,
        primary: NextAction | None,
        secondary: NextAction | None = None,
        hint: str | None = None,
    ) -> None:
        self._primary = primary
        self._secondary = secondary
        self._apply(self.primary_button, primary)
        self._apply(self.secondary_button, secondary)
        self.hint_label.setText(hint or "")
        # An empty footer is not drawn (an empty state already says what to do).
        self.setVisible(bool(primary or secondary or hint))

    @staticmethod
    def _apply(button: QPushButton, action: NextAction | None) -> None:
        if action is None:
            button.hide()
            return
        button.setText(action.label)
        button.setEnabled(action.enabled)
        button.setToolTip(action.tooltip or "")
        button.setAccessibleName(action.label)
        button.show()

    @property
    def primary_action(self) -> NextAction | None:
        return self._primary

    def _run_primary(self) -> None:
        if self._primary is not None:
            self._primary.callback()

    def _run_secondary(self) -> None:
        if self._secondary is not None:
            self._secondary.callback()


# ── Read popover ──


class ReadPopover(QFrame):
    """ "⟳ Reading DCS World…" under the 1. Setup tab: what is kept, Read again,
    Turn off automatic reading. A frameless tool window that never takes focus."""

    read_again = Signal()
    toggle_automatic = Signal(bool)  # the new value

    def __init__(self, parent: QWidget | None = None):
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setObjectName("readPopover")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setStyleSheet(POPOVER_QSS)
        self.setFixedWidth(340)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 12, 12)
        root.setSpacing(8)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(14, 14)
        head.addWidget(self.status_icon)
        self.title_label = QLabel("")
        self.title_label.setObjectName("popoverTitle")
        self.title_label.setWordWrap(True)
        head.addWidget(self.title_label, 1)
        close = QToolButton()
        close.setIcon(qta.icon("fa5s.times", color="#9AA0A6"))
        close.setIconSize(QSize(12, 12))
        close.setFixedSize(22, 22)
        close.setAutoRaise(True)
        close.setToolTip(S.BANNER_DISMISS)
        close.clicked.connect(self.hide)
        head.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(head)
        self.kept_label = QLabel(S.READ_POPOVER_KEPT)
        self.kept_label.setObjectName("popoverKept")
        self.kept_label.setWordWrap(True)
        root.addWidget(self.kept_label)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.read_again_button = QPushButton(S.READ_AGAIN)
        self.read_again_button.clicked.connect(self.read_again.emit)
        buttons.addWidget(self.read_again_button)
        self.auto_button = QPushButton(S.TURN_OFF_AUTOMATIC_READING)
        self.auto_button.clicked.connect(self._toggle)
        buttons.addWidget(self.auto_button)
        buttons.addStretch(1)
        root.addLayout(buttons)
        self._spin: qta.Spin | None = None
        self._automatic = True

    def set_reading(self, title: str) -> None:
        self.title_label.setText(title)
        self.read_again_button.setEnabled(False)
        self._spin = qta.Spin(self.status_icon, interval=12, step=6)
        self.status_icon.setPixmap(
            qta.icon("fa5s.sync", color="#4C8BF5", animation=self._spin).pixmap(14, 14)
        )

    def set_idle(self, title: str, ok: bool = True) -> None:
        if self._spin is not None:
            self._spin.stop()
            self._spin = None
        self.title_label.setText(title)
        self.read_again_button.setEnabled(True)
        name, colour = (
            ("fa5s.check-circle", "#34D399")
            if ok
            else ("fa5s.exclamation-triangle", "#F59E0B")
        )
        self.status_icon.setPixmap(qta.icon(name, color=colour).pixmap(14, 14))

    def set_automatic(self, automatic: bool) -> None:
        self._automatic = automatic
        self.auto_button.setText(
            S.TURN_OFF_AUTOMATIC_READING if automatic else S.TURN_ON_AUTOMATIC_READING
        )

    def _toggle(self) -> None:
        self.set_automatic(not self._automatic)
        self.toggle_automatic.emit(self._automatic)

    def show_under(self, anchor: QWidget) -> None:
        self.adjustSize()
        bottom_left = anchor.mapToGlobal(QPoint(0, anchor.height() + 6))
        self.move(bottom_left)
        self.show()


# ── Game reader ──


class ExecutorSignals(QObject):
    started = Signal()
    processed = Signal(object)
    process_error = Signal(object)
    finished = Signal()


class PluginExecutor(QRunnable):
    """Reads every enabled game once on a worker thread (one ``PluginWrapper.process``
    each) and reports per game; a failed game does not stop the others."""

    def __init__(self, plugin_wrappers: list[PluginWrapper]):
        super().__init__()
        self.plugin_wrappers = plugin_wrappers
        self.signals = ExecutorSignals()

    @Slot()
    def run(self):
        self.signals.started.emit()
        for plugin in self.plugin_wrappers:
            if not plugin.enabled:
                _logger.info(f"Game {plugin.name} is turned off - skipping")
                continue
            if not plugin.process():
                _logger.error(f"Reading {plugin.name} failed")
                self.signals.process_error.emit(plugin)
                continue  # one game failing never stops the others
            self.signals.processed.emit(plugin)
        self.signals.finished.emit()


class GameReader(QObject):
    """Runs a read of the enabled, ready games in the background and finishes it
    on the UI thread: profiles reprocessed, inventory recorded, ``ReadOutcome``
    emitted. One read at a time (``in_progress``)."""

    started = Signal(list)  # game names
    game_read = Signal(object)  # PluginWrapper
    game_failed = Signal(object)  # PluginWrapper
    finished = Signal(object)  # ReadOutcome

    def __init__(self, app_state: Any, parent: QObject | None = None):
        super().__init__(parent)
        self.app_state = app_state
        self._pool = QThreadPool.globalInstance()
        self._worker: PluginExecutor | None = None
        self._wrappers: list[PluginWrapper] = []
        self._failed: dict[str, str] = {}
        self._read: list[str] = []
        self._previous: dict[int, Any] = {}
        self.last_outcome: ReadOutcome | None = None

    @property
    def in_progress(self) -> bool:
        return self._worker is not None

    def readable_games(self) -> list[PluginWrapper]:
        manager = getattr(self.app_state, "plugin_manager", None)
        wrappers = getattr(manager, "plugin_wrappers", None) or []
        return [w for w in wrappers if w.enabled and w.ready]

    def start(self, wrappers: Iterable[PluginWrapper] | None = None) -> bool:
        """Start a read; ``False`` when one is running or nothing can be read."""
        if self.in_progress:
            return False
        selected = list(wrappers) if wrappers is not None else self.readable_games()
        selected = [w for w in selected if w.enabled and w.ready]
        if not selected:
            return False
        self._wrappers = selected
        self._failed = {}
        self._read = []
        # The last good read is kept when a game can't be read this time (J14 #4).
        self._previous = {id(w): w.plugin_profile_collection for w in selected}
        self._worker = PluginExecutor(selected)
        self._worker.signals.processed.connect(self._on_processed)
        self._worker.signals.process_error.connect(self._on_failed)
        self._worker.signals.finished.connect(self._on_finished)
        self.started.emit([w.name for w in selected])
        self._pool.start(self._worker)
        return True

    @Slot(object)
    def _on_processed(self, wrapper: PluginWrapper) -> None:
        self._read.append(wrapper.name)
        self.game_read.emit(wrapper)

    @Slot(object)
    def _on_failed(self, wrapper: PluginWrapper) -> None:
        self._failed[wrapper.name] = wrapper.error or ""
        self.game_failed.emit(wrapper)

    @Slot()
    def _on_finished(self) -> None:
        for wrapper in self._wrappers:
            if (
                wrapper.name in self._failed
                and wrapper.plugin_profile_collection is None
            ):
                wrapper.plugin_profile_collection = self._previous.get(id(wrapper))
        self._previous = {}
        outcome = ReadOutcome(
            games=[w.name for w in self._wrappers],
            failed=dict(self._failed),
            finished_at=now_time_text(),
        )
        try:
            self.app_state.process_profiles_from_collections()
        except Exception as error:  # noqa: BLE001 - a bad profile must not kill the shell
            _logger.error(
                f"Processing the read bindings failed: {error}", exc_info=True
            )
        for wrapper in self._wrappers:
            if wrapper.name in self._failed:
                continue
            collection = wrapper.plugin_profile_collection
            count = len(collection) if collection else 0
            outcome.profiles_per_game[wrapper.name] = count
            outcome.profile_count += count
        if outcome.profile_count or self._read:
            try:
                outcome.inventory = self.app_state.record_device_read()
            except Exception as error:  # noqa: BLE001 - inventory is a convenience
                _logger.error(f"Recording the read failed: {error}", exc_info=True)
        self._worker = None
        self.last_outcome = outcome
        self.finished.emit(outcome)


# ── Placeholder pages ──


def profile_count(app_state: Any) -> int:
    return len(getattr(app_state, "profile_wrappers", None) or [])


def bindings_placeholder_status(app_state: Any) -> StageStatus:
    count = profile_count(app_state)
    if count == 0:
        return StageStatus("none", S.STATUS_PLACEHOLDER_BINDINGS)
    return StageStatus(
        "none",
        S.STATUS_PLACEHOLDER_BINDINGS_PROFILES.format(
            count=count, profiles=S.plural(count, *S.PROFILES)
        ),
        done=True,
    )


def diagrams_placeholder_status(app_state: Any) -> StageStatus:
    """ "Nothing to export yet" / "Choose templates first" / "N diagrams ready"."""
    from joystick_diagrams.device_status import all_device_statuses

    wrappers = getattr(app_state, "profile_wrappers", None) or []
    if not wrappers:
        return StageStatus("none", S.STATUS_PLACEHOLDER_DIAGRAMS_NONE)
    try:
        statuses = all_device_statuses(wrappers, include_unseen=False)
    except Exception as error:  # noqa: BLE001 - a placeholder must not fail the strip
        _logger.debug(f"Could not compute diagram status: {error}")
        return StageStatus("none", S.STATUS_PLACEHOLDER_DIAGRAMS_NONE)
    ready = sum(info.profile_count for info in statuses.values() if info.state.exports)
    needs = any(
        info.state.value in ("needs_template", "template_missing")
        for info in statuses.values()
    )
    if ready:
        return StageStatus(
            "ok",
            S.STATUS_PLACEHOLDER_DIAGRAMS_READY.format(
                count=ready, diagrams=S.plural(ready, *S.DIAGRAMS)
            ),
        )
    if needs:
        return StageStatus("none", S.STATUS_PLACEHOLDER_DIAGRAMS_CHOOSE)
    return StageStatus("none", S.STATUS_PLACEHOLDER_DIAGRAMS_NONE)


class PlaceholderStagePage(QWidget):
    """A stage page that says where to go while the real page is unavailable."""

    request_stage = Signal(int, dict)

    def __init__(self, stage: int, app_state: Any, parent: QWidget | None = None):
        super().__init__(parent)
        self.stage = stage
        self.app_state = app_state
        message = (
            S.PLACEHOLDER_BINDINGS
            if stage == STAGE_BINDINGS
            else S.PLACEHOLDER_DIAGRAMS
        )
        action = (
            S.PLACEHOLDER_GO_TO_SETUP
            if stage == STAGE_BINDINGS
            else S.PLACEHOLDER_GO_TO_CONTROLLERS
        )
        self._target = STAGE_SETUP if stage == STAGE_BINDINGS else STAGE_CONTROLLERS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        self.empty_state = EmptyState(message, "fa5s.hourglass-half", action)
        self.empty_state.action_requested.connect(
            lambda: self.request_stage.emit(self._target, {})
        )
        layout.addWidget(self.empty_state)

    def refresh(self) -> None:
        pass

    def stage_status(self) -> StageStatus:
        if self.stage == STAGE_BINDINGS:
            return bindings_placeholder_status(self.app_state)
        if self.stage == STAGE_DIAGRAMS:
            return diagrams_placeholder_status(self.app_state)
        return StageStatus("none", S.STATUS_PLACEHOLDER_UNAVAILABLE)

    def next_action(self) -> NextAction | None:
        return None

    def handle_request(self, payload: dict) -> None:
        _logger.debug(f"Placeholder stage {self.stage} ignored deep link {payload}")

    navigate = handle_request


if __name__ == "__main__":
    pass
