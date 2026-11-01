"""Stage 3, "3. Bindings" (journey board J07): check what each control says.

A settings-style nav on the left, **Bindings | Shared bindings | Labels**,
wrapping three screens:

- ``CustomiseProfiles`` (Bindings): opens on a Ready controller; the profile
  picker lists only profiles with bindings on it; Edit label / F2 /
  double-click relabels; inherited bindings show where they come from with a
  link to Shared bindings.
- ``CustomiseInheritance`` (Shared bindings): which profiles a profile uses
  bindings from, and the clash rule (moved here from Settings › General).
- ``CustomiseLabels`` (Labels): every label, with "Only labels used on
  <controller>".

Shell contract (``ui/stage_contract.py``): ``refresh()``, ``stage_status()``
→ ("none", "Optional · N profiles"), ``next_action()`` → "Next: 4. Diagrams ›",
``request_stage`` and ``navigate(payload)`` / ``handle_request(payload)`` for
deep links (``{"device_guid": …}`` selects that controller, ``{"section":
"shared" | "labels" | "bindings"}`` opens a screen). Nothing here blocks export.
"""

from __future__ import annotations

import logging
from typing import Any

import qtawesome as qta
from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.ui import strings_bindings as S
from joystick_diagrams.ui.customise_inheritance import CustomiseInheritance
from joystick_diagrams.ui.customise_labels import CustomiseLabels
from joystick_diagrams.ui.customise_profiles import CustomiseProfiles
from joystick_diagrams.ui.stage_contract import (
    PAYLOAD_DEVICE_GUID,
    PAYLOAD_SECTION,
    SECTION_APPEARANCE,
    SECTION_LAYOUT,
    STAGE_DIAGRAMS,
    NextAction,
    StageStatus,
)

_logger = logging.getLogger(__name__)

SECTION_BINDINGS = "bindings"
SECTION_SHARED = "shared"
SECTION_LABELS = "labels"
SECTIONS = (SECTION_BINDINGS, SECTION_SHARED, SECTION_LABELS)
PAYLOAD_PROFILE_KEY = "profile_key"


def _statuses(wrappers: list[Any]) -> dict:
    try:
        from joystick_diagrams.device_status import all_device_statuses

        return all_device_statuses(wrappers, include_unseen=False)
    except Exception as error:  # noqa: BLE001 - the screens still work without them
        _logger.warning(f"Could not work out controller statuses: {error}")
        return {}


class BindingsPage(QWidget):
    request_stage = Signal(int, dict)
    state_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.setProperty("class", "settings-nav")
        self.nav_list.setAccessibleName(S.TITLE)
        for icon_name, label in (
            ("fa5s.list", S.NAV_BINDINGS),
            ("fa5s.code-branch", S.NAV_SHARED),
            ("fa5s.tags", S.NAV_LABELS),
        ):
            item = QListWidgetItem(qta.icon(icon_name, color="#9AA0A6"), label)
            item.setSizeHint(QSize(0, 44))
            self.nav_list.addItem(item)
        root.addWidget(self.nav_list)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 0)
        content_layout.setSpacing(4)
        self.heading = QLabel(S.TITLE)
        self.heading.setObjectName("heading_label")
        content_layout.addWidget(self.heading)
        self.intro = QLabel(S.INTRO)
        self.intro.setObjectName("device_help_label")
        self.intro.setWordWrap(True)
        content_layout.addWidget(self.intro)

        self.stack = QStackedWidget()
        self.profiles_screen = CustomiseProfiles()
        self.inheritance_screen = CustomiseInheritance()
        self.labels_screen = CustomiseLabels()
        for screen in (
            self.profiles_screen,
            self.inheritance_screen,
            self.labels_screen,
        ):
            self.stack.addWidget(screen)
        content_layout.addWidget(self.stack, 1)
        root.addWidget(content, 1)

        self.profiles_screen.open_shared_requested.connect(self.show_shared)
        self.profiles_screen.labels_changed.connect(self._on_labels_changed)
        self.labels_screen.labels_changed.connect(self._on_labels_changed)
        self.inheritance_screen.bindings_changed.connect(self._on_bindings_changed)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self._loaded = False
        self.nav_list.setCurrentRow(0)

    # ── Shell contract ──

    def refresh(self) -> None:
        statuses = _statuses(list(self.appState.profile_wrappers))
        self.profiles_screen.refresh(statuses)
        current = self.stack.currentWidget()
        if current is not self.profiles_screen:
            current.refresh()
        self._loaded = True

    def stage_status(self) -> StageStatus:
        count = len(self.appState.profile_wrappers)
        if not count:
            return StageStatus("none", S.STATUS_OPTIONAL)
        return StageStatus(
            "none",
            S.STATUS_OPTIONAL_PROFILES.format(
                count=count, profiles=S.plural(count, *S.PROFILES)
            ),
        )

    def next_action(self) -> NextAction | None:
        return NextAction(S.NEXT_DIAGRAMS, self.go_to_diagrams)

    def go_to_diagrams(self) -> None:
        self.request_stage.emit(STAGE_DIAGRAMS, {})

    def navigate(self, payload: dict) -> None:
        """Deep link: ``device_guid`` selects a controller, ``section`` a screen."""
        payload = payload or {}
        section = payload.get(PAYLOAD_SECTION)
        if section in (SECTION_APPEARANCE, SECTION_LAYOUT):
            self.request_stage.emit(STAGE_DIAGRAMS, dict(payload))
            return
        if not self._loaded:
            self.refresh()
        guid = payload.get(PAYLOAD_DEVICE_GUID)
        if section in SECTIONS:
            self.show_section(section)
        elif guid:
            self.show_section(SECTION_BINDINGS)
        if guid:
            self.profiles_screen.select_controller(guid)
            if self.stack.currentWidget() is self.labels_screen:
                self.labels_screen.set_filter_device(guid)
        profile_key = payload.get(PAYLOAD_PROFILE_KEY)
        if profile_key:
            self.profiles_screen.select_profile(profile_key)
            self.inheritance_screen.select_profile(profile_key)

    handle_request = navigate

    # ── Sections ──

    def show_section(self, section: str) -> None:
        if section in SECTIONS:
            self.nav_list.setCurrentRow(SECTIONS.index(section))

    def current_section(self) -> str:
        return SECTIONS[max(self.nav_list.currentRow(), 0)]

    def _on_nav_changed(self, row: int) -> None:
        if row < 0:
            return
        self.stack.setCurrentIndex(row)
        self.heading.setText((S.NAV_BINDINGS, S.NAV_SHARED, S.NAV_LABELS)[row])
        self.intro.setVisible(row == 0)
        current = self.stack.currentWidget()
        if current is self.inheritance_screen:
            current.refresh()
            self.inheritance_screen.select_profile(
                self.profiles_screen.current_profile_key()
            )
        elif current is self.labels_screen:
            current.refresh()
        elif current is self.profiles_screen and self._loaded:
            self.profiles_screen.refresh()

    def show_shared(self, profile_key: str | None = None) -> None:
        """Open Shared bindings on ``profile_key`` (default: the Bindings profile)."""
        key = profile_key or self.profiles_screen.current_profile_key()
        self.show_section(SECTION_SHARED)
        self.inheritance_screen.select_profile(key)

    def _on_labels_changed(self) -> None:
        self.state_changed.emit()

    def _on_bindings_changed(self) -> None:
        self.profiles_screen.refresh()
        self.state_changed.emit()


if __name__ == "__main__":
    pass
