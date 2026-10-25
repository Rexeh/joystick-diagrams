"""Stage 2, Controllers (boards J04–J06): every controller from the latest read,
grouped Needs a template / Ready / No diagram / Not in your latest bindings, with
a detail panel whose Template section comes first.

Statuses come from ``device_status.all_device_statuses`` only, so this page, the
results card on 1. Setup and the strip always agree. Before any read in this
session the list is drawn from what the app remembers (``snapshot_statuses``):
the template and "No diagram" choices stored per controller and the games it was
last seen in. Before anything was ever read the page is an empty state that
links back to 1. Setup.

The page follows the stage contract (``ui/stage_contract.py``): ``refresh()``
rebuilds in place (selection kept), ``stage_status()``, ``next_action()``,
``request_stage`` for "Edit layout ›" (4. Diagrams, section layout) and
"View bindings ›" (3. Bindings), and ``handle_request({"device_guid": …,
"action": "choose_template"})``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams import template_catalog
from joystick_diagrams.app_state import AppState
from joystick_diagrams.device_status import (
    DeviceStatus,
    StatusInfo,
    StatusSources,
    all_device_statuses,
    collect_device_facts,
    reason_text,
)
from joystick_diagrams.ui import strings_controllers as S
from joystick_diagrams.ui.stage_contract import (
    PAYLOAD_DEVICE_GUID,
    PAYLOAD_SECTION,
    SECTION_LAYOUT,
    STAGE_BINDINGS,
    STAGE_DIAGRAMS,
    STAGE_SETUP,
    NextAction,
    StageStatus,
)
from joystick_diagrams.ui.widgets.empty_state import EmptyState

_logger = logging.getLogger(__name__)

GROUP_NEEDS = "needs"
GROUP_READY = "ready"
GROUP_NO_DIAGRAM = "no_diagram"
GROUP_NOT_SEEN = "not_seen"
GROUP_ORDER = (GROUP_NEEDS, GROUP_READY, GROUP_NO_DIAGRAM, GROUP_NOT_SEEN)
GROUP_TITLES = {
    GROUP_NEEDS: S.GROUP_NEEDS_TEMPLATE,
    GROUP_READY: S.GROUP_READY,
    GROUP_NO_DIAGRAM: S.GROUP_NO_DIAGRAM,
    GROUP_NOT_SEEN: S.GROUP_NOT_SEEN,
}
GROUP_COLLAPSED = {GROUP_NO_DIAGRAM, GROUP_NOT_SEEN}

ROLE_GUID = Qt.ItemDataRole.UserRole
ROLE_GROUP = Qt.ItemDataRole.UserRole + 1

COLOUR_OK = "#34D399"
COLOUR_WARNING = "#F59E0B"
COLOUR_MUTED = "#9AA0A6"

THUMB_WIDTH = 220

PAGE_QSS = """
QPushButton, QToolButton { text-transform: none; }
QCheckBox { background: transparent; }
QLabel { background: transparent; }
QLabel#ctrlTitle { color: #E8EAED; font-size: 18px; font-weight: 700; }
QLabel#ctrlSubtitle { color: #9AA0A6; font-size: 12px; }
QLabel#detailName { color: #E8EAED; font-size: 16px; font-weight: 700; }
QLabel#sectionTitle { color: #9AA0A6; font-size: 11px; font-weight: 700; }
QLabel#templateName { color: #E8EAED; font-size: 13px; font-weight: 700; }
QLabel#muted { color: #9AA0A6; font-size: 12px; }
QLabel#fitLine { color: #E8EAED; font-size: 12px; }
QLabel#fitLine[state="ok"] { color: #34D399; }
QLabel#fitLine[state="warning"] { color: #F59E0B; }
QLabel#rowName { color: #E8EAED; font-size: 12px; font-weight: 700; }
QLabel#rowStatus { color: #9AA0A6; font-size: 11px; }
QLabel#problem { color: #F87171; font-size: 12px; }
QFrame#templateSection {
    background: #252830; border: 1px solid #3C4043; border-radius: 8px;
}
QFrame#templateSection[state="warning"] { border-left: 3px solid #F59E0B; }
QFrame#templateSection[state="ok"] { border-left: 3px solid #34D399; }
QFrame#moreSection { background: transparent; }
QTreeWidget#controllerList { background: #252830; border: 1px solid #3C4043; border-radius: 6px; }
QPushButton#ctrlAction {
    background: #2c2f38; color: #E8EAED; border: 1px solid #7A808A; border-radius: 4px;
    min-height: 30px; padding: 0px 14px; font-size: 11px; font-weight: 700;
}
QPushButton#ctrlAction:hover { border-color: #4C8BF5; }
QPushButton#ctrlAction:focus { border: 2px solid #4C8BF5; }
QPushButton#ctrlAction:disabled { color: #6B7280; border-color: #3C4043; }
QPushButton#ctrlPrimary {
    background: #2F6FDB; color: #ffffff; border: 1px solid #2F6FDB; border-radius: 4px;
    min-height: 30px; padding: 0px 14px; font-size: 11px; font-weight: 700;
}
QPushButton#ctrlPrimary:hover { background: #4C8BF5; border-color: #4C8BF5; }
QPushButton#ctrlPrimary:focus { border: 2px solid #8AB4F8; }
QPushButton#ctrlLink {
    background: transparent; border: none; color: #8AB4F8; padding: 2px 0px;
    text-align: left; font-size: 12px;
}
QPushButton#ctrlLink:hover { text-decoration: underline; }
"""


# ── Status grouping (shared with 1. Setup) ──


def group_of(info: StatusInfo) -> str | None:
    if info.state in (DeviceStatus.NEEDS_TEMPLATE, DeviceStatus.TEMPLATE_MISSING):
        return GROUP_NEEDS
    if info.state.exports:
        return GROUP_READY
    if info.state in (DeviceStatus.NO_DIAGRAM, DeviceStatus.MERGED):
        return GROUP_NO_DIAGRAM
    if info.state is DeviceStatus.NOT_SEEN:
        return GROUP_NOT_SEEN
    return None  # NO_PROFILES: nothing to show


@dataclass
class ControllerSummary:
    """Counts for the strip, the footer and the results card."""

    statuses: dict[str, StatusInfo] = field(default_factory=dict)
    snapshot: bool = False  # drawn from what the app remembers (no read yet)

    def guids_in(self, group: str) -> list[str]:
        rows = [g for g, info in self.statuses.items() if group_of(info) == group]
        return sorted(rows, key=lambda g: (self.statuses[g].name or g).casefold())

    @property
    def needs(self) -> list[str]:
        return self.guids_in(GROUP_NEEDS)

    @property
    def ready(self) -> list[str]:
        return self.guids_in(GROUP_READY)

    @property
    def no_diagram(self) -> list[str]:
        return self.guids_in(GROUP_NO_DIAGRAM)

    @property
    def not_seen(self) -> list[str]:
        return self.guids_in(GROUP_NOT_SEEN)

    @property
    def found(self) -> list[str]:
        """Controllers in the latest read (``needs + ready + no_diagram``)."""
        return self.needs + self.ready + self.no_diagram

    @property
    def is_empty(self) -> bool:
        return not any(group_of(info) for info in self.statuses.values())

    @property
    def first_read(self) -> bool:
        """Every controller is new: the first read, so nothing is "new" yet."""
        found = self.found
        return bool(found) and all(self.statuses[g].is_new for g in found)

    def is_new(self, guid: str) -> bool:
        info = self.statuses.get(guid)
        return bool(info and info.is_new and not self.first_read)

    @property
    def new_needing_template(self) -> list[str]:
        return [g for g in self.needs if self.is_new(g)]

    @property
    def diagram_count(self) -> int:
        return sum(self.statuses[g].profile_count for g in self.ready)


_TEMPLATE_CACHE: dict[str, Any] = {}


def compute_statuses(
    profile_wrappers: Iterable[Any] | None = None,
    *,
    relink: bool = False,
    template_cache: dict[str, Any] | None = None,
) -> ControllerSummary:
    """Every controller's status. ``relink=False`` never writes (strip, results card)."""
    state = AppState()
    wrappers = list(
        state.profile_wrappers if profile_wrappers is None else profile_wrappers
    )
    if not wrappers:
        return ControllerSummary(snapshot_statuses(), snapshot=True)
    sources = StatusSources.from_app_state()
    sources.relink = relink
    sources.template_cache = (
        _TEMPLATE_CACHE if template_cache is None else template_cache
    )
    try:
        statuses = all_device_statuses(wrappers, sources, include_unseen=True)
    except Exception as error:  # noqa: BLE001 - never let a status break a screen
        _logger.error(f"Could not work out controller statuses: {error}", exc_info=True)
        statuses = {}
    return ControllerSummary(statuses)


def clear_template_cache() -> None:
    _TEMPLATE_CACHE.clear()


def snapshot_statuses() -> dict[str, StatusInfo]:
    """Statuses from what the app remembers, before this session's first read."""
    state = AppState()
    service = state.device_service
    inventory = getattr(state, "device_inventory_service", None)
    guids: set[str] = set()
    if inventory is not None:
        guids.update(inventory.known_guids())
    statuses: dict[str, StatusInfo] = {}
    for guid in sorted(guids):
        row = service.row(guid)
        entry = inventory.entry(guid) if inventory is not None else None
        name = (row.name if row else None) or (entry.name if entry else None) or guid
        name = service.resolve_name(guid, name)
        games = row.games if row else {}
        common = {
            "name": name,
            "games": games,
            "profile_count": sum(games.values()),
        }
        kind = service.kind(guid)
        alias_target = state.device_alias_service.resolve(guid)
        if alias_target != guid:
            statuses[guid] = StatusInfo(
                DeviceStatus.MERGED, "merged_into", merged_into=alias_target, **common
            )
        elif kind is not None and kind.no_diagram:
            statuses[guid] = StatusInfo(
                DeviceStatus.NO_DIAGRAM,
                kind.reason or "user",
                kind_source=kind.source,
                **common,
            )
        elif row is not None and row.template_path:
            statuses[guid] = StatusInfo(
                DeviceStatus.READY,
                template_name=Path(row.template_path).name,
                template_path=row.template_path,
                template_key=row.template_key,
                **common,
            )
        else:
            statuses[guid] = StatusInfo(DeviceStatus.NEEDS_TEMPLATE, **common)
    return statuses


# ── Words for a row ──


def template_display_name(info: StatusInfo) -> str:
    path = info.template_path
    if not path:
        return Path(info.template_name).stem if info.template_name else ""
    try:
        catalogue_info = template_catalog.info_for_path(Path(path))
    except Exception:  # noqa: BLE001 - a file outside the catalogue keeps its name
        return Path(path).stem
    if in_my_templates(catalogue_info):
        return S.ROW_MY_TEMPLATE.format(name=catalogue_info.name)
    return catalogue_info.name


def in_my_templates(catalogue_info: Any) -> bool:
    from joystick_diagrams import utils

    return (
        catalogue_info.source != "bundled"
        and catalogue_info.maker == utils.USER_TEMPLATES_DIR_NAME
    )


def source_parts(catalogue_info: Any) -> list[str]:
    """ "VKB Sim · Included with the app", "My templates", or the file's folder."""
    if catalogue_info is None:
        return []
    if catalogue_info.source == "bundled":
        return [p for p in (catalogue_info.maker, S.INCLUDED_WITH_APP) if p]
    if in_my_templates(catalogue_info):
        return [S.MY_TEMPLATES]
    return [catalogue_info.maker] if catalogue_info.maker else []


def short_date(stamp: str | None) -> str:
    if not stamp:
        return ""
    try:
        moment = datetime.fromisoformat(stamp)
    except ValueError:
        return stamp[:10]
    if moment.year == datetime.now().year:
        return f"{moment.day} {moment.strftime('%b')}"
    return f"{moment.day} {moment.strftime('%b')} {moment.year}"


def merged_name(info: StatusInfo, statuses: dict[str, StatusInfo]) -> str | None:
    if not info.merged_into:
        return None
    target = statuses.get(info.merged_into)
    if target is not None and target.name:
        return target.name
    service = AppState().device_service
    row = service.row(info.merged_into)
    return (
        service.resolve_name(info.merged_into, row.name) if row and row.name else None
    )


def row_status_text(
    guid: str, info: StatusInfo, statuses: dict[str, StatusInfo] | None = None
) -> str:
    profiles = S.counted(info.profile_count, S.PROFILES)
    if info.state is DeviceStatus.NEEDS_TEMPLATE:
        return S.ROW_NO_TEMPLATE.format(
            count=info.profile_count, profiles=S.plural(info.profile_count, S.PROFILES)
        )
    if info.state is DeviceStatus.TEMPLATE_MISSING:
        return S.ROW_TEMPLATE_MISSING.format(
            name=info.template_name or "",
            count=info.profile_count,
            profiles=S.plural(info.profile_count, S.PROFILES),
        )
    if info.state is DeviceStatus.READY_WITH_GAPS:
        gaps = len(info.missing_controls)
        return S.ROW_READY_GAPS.format(
            template=template_display_name(info),
            count=gaps,
            bindings=S.plural(gaps, S.BINDINGS),
        )
    if info.state is DeviceStatus.READY:
        return f"{template_display_name(info)} · {profiles}"
    if info.state is DeviceStatus.MERGED:
        return (
            reason_text("merged_into", merged_name=merged_name(info, statuses or {}))
            or ""
        )
    if info.state is DeviceStatus.NO_DIAGRAM:
        return reason_text(info.reason, info.template_name) or ""
    if info.state is DeviceStatus.NOT_SEEN:
        inventory = getattr(AppState(), "device_inventory_service", None)
        entry = inventory.entry(guid) if inventory is not None else None
        date = short_date(entry.last_seen if entry else None)
        return S.ROW_NOT_SEEN.format(date=date) if date else S.ROW_NOT_SEEN_NO_DATE
    return ""


def row_icon(info: StatusInfo) -> tuple[str, str]:
    if info.state in (
        DeviceStatus.NEEDS_TEMPLATE,
        DeviceStatus.TEMPLATE_MISSING,
        DeviceStatus.READY_WITH_GAPS,
    ):
        return "fa5s.exclamation-triangle", COLOUR_WARNING
    if info.state is DeviceStatus.READY:
        return "fa5s.check-circle", COLOUR_OK
    if info.state is DeviceStatus.NOT_SEEN:
        return "fa5s.clock", COLOUR_MUTED
    return "fa5s.minus-circle", COLOUR_MUTED


def used_in_text(info: StatusInfo) -> str:
    if not info.games:
        return S.USED_IN_NONE
    entries = [
        S.USED_IN_ENTRY.format(
            game=game, count=count, profiles=S.plural(count, S.PROFILES)
        )
        for game, count in sorted(
            info.games.items(), key=lambda item: (-item[1], item[0])
        )
    ]
    return S.USED_IN.format(games=", ".join(entries))


# ── Widgets ──


class ControllerRow(QWidget):
    """One row: status icon, name and the status line."""

    def __init__(
        self,
        guid: str,
        info: StatusInfo,
        text: str,
        parent: QWidget | None = None,
        show_new: bool = True,
    ):
        super().__init__(parent)
        self.guid = guid
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 8, 4)
        layout.setSpacing(8)
        icon_name, colour = row_icon(info)
        self.icon = QLabel()
        self.icon.setPixmap(qta.icon(icon_name, color=colour).pixmap(QSize(14, 14)))
        self.icon.setFixedSize(14, 14)
        layout.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(1)
        name = info.name or guid
        self.name_label = QLabel(name)
        self.name_label.setObjectName("rowName")
        column.addWidget(self.name_label)
        self.status_label = QLabel(text)
        self.status_label.setObjectName("rowStatus")
        column.addWidget(self.status_label)
        layout.addLayout(column, 1)
        if show_new and info.is_new and info.state is not DeviceStatus.NOT_SEEN:
            badge = QLabel(S.ROW_NEW)
            badge.setStyleSheet(
                "color: #8AB4F8; background: rgba(76,139,245,0.15); border-radius: 3px;"
                " padding: 1px 6px; font-size: 10px;"
            )
            layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        self.setAccessibleName(f"{name}, {text}")


class ControllersPage(QWidget):
    request_stage = Signal(int, dict)
    state_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()
        self.setStyleSheet(PAGE_QSS)
        self.summary = ControllerSummary()
        self._selected_guid: str | None = None
        self._rows: dict[str, QTreeWidgetItem] = {}
        self._thumb_generation = 0
        self._pool = QThreadPool.globalInstance()
        from joystick_diagrams.ui.template_picker import _WorkerSignals

        self._thumb_signals = _WorkerSignals(self)
        self._thumb_signals.thumb_ready.connect(self._on_thumb_ready)
        self._thumb_key: str | None = None
        self._preview_window = None
        self._build_ui()
        self.refresh()

    # ── Construction ──

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 12)
        root.setSpacing(10)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.empty_state = EmptyState(S.EMPTY_MESSAGE, "fa5s.gamepad", S.EMPTY_ACTION)
        self.empty_state.action_requested.connect(
            lambda: self.request_stage.emit(STAGE_SETUP, {})
        )
        self.stack.addWidget(self.empty_state)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)
        self.title_label = QLabel(S.TITLE)
        self.title_label.setObjectName("ctrlTitle")
        content_layout.addWidget(self.title_label)
        self.subtitle_label = QLabel(S.SUBTITLE_CHOOSE)
        self.subtitle_label.setObjectName("ctrlSubtitle")
        self.subtitle_label.setWordWrap(True)
        content_layout.addWidget(self.subtitle_label)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.tree = QTreeWidget()
        self.tree.setObjectName("controllerList")
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(1)
        self.tree.setIndentation(10)
        self.tree.setMinimumWidth(300)
        self.tree.currentItemChanged.connect(self._on_current_changed)
        self.splitter.addWidget(self.tree)

        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.detail_scroll.setWidget(self._build_detail())
        self.splitter.addWidget(self.detail_scroll)
        self.splitter.setStretchFactor(0, 40)
        self.splitter.setStretchFactor(1, 60)
        content_layout.addWidget(self.splitter, 1)
        self.stack.addWidget(content)

    def _build_detail(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 4, 4, 4)
        layout.setSpacing(12)

        self.no_selection = QLabel(S.SELECT_A_CONTROLLER)
        self.no_selection.setObjectName("muted")
        self.no_selection.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.no_selection)

        self.detail = QWidget()
        detail = QVBoxLayout(self.detail)
        detail.setContentsMargins(0, 0, 0, 0)
        detail.setSpacing(12)
        self.detail_name = QLabel("")
        self.detail_name.setObjectName("detailName")
        self.detail_name.setWordWrap(True)
        detail.addWidget(self.detail_name)

        # Template section, first.
        self.template_section = QFrame()
        self.template_section.setObjectName("templateSection")
        section = QVBoxLayout(self.template_section)
        section.setContentsMargins(14, 12, 14, 12)
        section.setSpacing(8)
        heading = QLabel(S.SECTION_TEMPLATE.upper())
        heading.setObjectName("sectionTitle")
        section.addWidget(heading)
        body = QHBoxLayout()
        body.setSpacing(14)
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(THUMB_WIDTH, 150)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setStyleSheet("background: #1f2229; border-radius: 6px;")
        body.addWidget(self.thumbnail, 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(4)
        self.template_name = QLabel("")
        self.template_name.setObjectName("templateName")
        self.template_name.setWordWrap(True)
        text.addWidget(self.template_name)
        self.template_source = QLabel("")
        self.template_source.setObjectName("muted")
        text.addWidget(self.template_source)
        self.fit_line = QLabel("")
        self.fit_line.setObjectName("fitLine")
        self.fit_line.setWordWrap(True)
        text.addWidget(self.fit_line)
        self.missing_toggle = QPushButton("")
        self.missing_toggle.setObjectName("ctrlLink")
        self.missing_toggle.setToolTip(S.MISSING_CONTROLS_TIP)
        self.missing_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.missing_toggle.clicked.connect(self._toggle_missing)
        text.addWidget(self.missing_toggle)
        self.missing_list = QLabel("")
        self.missing_list.setObjectName("muted")
        self.missing_list.setWordWrap(True)
        self.missing_list.hide()
        text.addWidget(self.missing_list)
        text.addStretch(1)
        body.addLayout(text, 1)
        section.addLayout(body)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.choose_button = QPushButton(S.CHOOSE_TEMPLATE)
        self.choose_button.setObjectName("ctrlPrimary")
        self.choose_button.clicked.connect(self.choose_template_for_selected)
        buttons.addWidget(self.choose_button)
        self.preview_button = QPushButton(S.PREVIEW)
        self.preview_button.setObjectName("ctrlAction")
        self.preview_button.clicked.connect(self._open_preview)
        buttons.addWidget(self.preview_button)
        self.edit_layout_button = QPushButton(S.EDIT_LAYOUT)
        self.edit_layout_button.setObjectName("ctrlAction")
        self.edit_layout_button.clicked.connect(self._edit_layout)
        buttons.addWidget(self.edit_layout_button)
        self.view_bindings_button = QPushButton(S.VIEW_BINDINGS)
        self.view_bindings_button.setObjectName("ctrlAction")
        self.view_bindings_button.clicked.connect(self._view_bindings)
        buttons.addWidget(self.view_bindings_button)
        buttons.addStretch(1)
        section.addLayout(buttons)
        detail.addWidget(self.template_section)

        # Make a diagram.
        diagram_row = QHBoxLayout()
        diagram_row.setSpacing(10)
        self.make_diagram = QCheckBox(S.MAKE_DIAGRAM)
        self.make_diagram.setToolTip(S.MAKE_DIAGRAM_TIP)
        self.make_diagram.toggled.connect(self._on_make_diagram_toggled)
        diagram_row.addWidget(self.make_diagram)
        self.reason_label = QLabel("")
        self.reason_label.setObjectName("muted")
        diagram_row.addWidget(self.reason_label, 1)
        detail.addLayout(diagram_row)

        self.used_in = QLabel("")
        self.used_in.setObjectName("muted")
        self.used_in.setWordWrap(True)
        detail.addWidget(self.used_in)

        # More.
        self.more_button = QToolButton()
        self.more_button.setText(S.MORE_SUMMARY)
        self.more_button.setCheckable(True)
        self.more_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.more_button.setArrowType(Qt.ArrowType.RightArrow)
        self.more_button.setAutoRaise(True)
        self.more_button.setStyleSheet("QToolButton { color: #8AB4F8; border: none; }")
        self.more_button.toggled.connect(self._toggle_more)
        detail.addWidget(self.more_button)
        detail.addWidget(self._build_more())
        detail.addStretch(1)
        layout.addWidget(self.detail)
        layout.addStretch(1)
        self.detail.hide()
        return panel

    def _build_more(self) -> QFrame:
        self.more = QFrame()
        self.more.setObjectName("moreSection")
        more = QVBoxLayout(self.more)
        more.setContentsMargins(18, 0, 0, 0)
        more.setSpacing(6)

        label = QLabel(S.NAME_ON_DIAGRAMS)
        label.setObjectName("sectionTitle")
        more.addWidget(label)
        name_row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setAccessibleName(S.NAME_ON_DIAGRAMS)
        self.name_edit.editingFinished.connect(self._on_name_edited)
        name_row.addWidget(self.name_edit, 1)
        self.name_reset = QToolButton()
        self.name_reset.setIcon(qta.icon("fa5s.undo", color=COLOUR_MUTED))
        self.name_reset.setToolTip(S.NAME_RESET_TIP)
        self.name_reset.setAccessibleName(S.NAME_RESET_TIP)
        self.name_reset.clicked.connect(self._on_name_reset)
        name_row.addWidget(self.name_reset)
        more.addLayout(name_row)

        label = QLabel(S.SAME_CONTROLLER_AS)
        label.setObjectName("sectionTitle")
        more.addWidget(label)
        self.same_combo = QComboBox()
        self.same_combo.setAccessibleName(S.SAME_CONTROLLER_AS)
        self.same_combo.setMaxVisibleItems(15)
        self.same_combo.currentIndexChanged.connect(self._on_same_changed)
        more.addWidget(self.same_combo)
        help_label = QLabel(S.SAME_CONTROLLER_HELP)
        help_label.setObjectName("muted")
        more.addWidget(help_label)
        self.same_problem = QLabel("")
        self.same_problem.setObjectName("problem")
        self.same_problem.setWordWrap(True)
        self.same_problem.hide()
        more.addWidget(self.same_problem)

        label = QLabel(S.CONTROLLER_ID)
        label.setObjectName("sectionTitle")
        more.addWidget(label)
        id_row = QHBoxLayout()
        self.id_label = QLabel("")
        self.id_label.setObjectName("muted")
        self.id_label.setStyleSheet("font-family: monospace;")
        self.id_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        id_row.addWidget(self.id_label, 1)
        self.copy_id = QPushButton(S.COPY_ID)
        self.copy_id.setObjectName("ctrlAction")
        self.copy_id.clicked.connect(self._copy_id)
        id_row.addWidget(self.copy_id)
        more.addLayout(id_row)
        self.more.hide()
        return self.more

    # ── Contract ──

    def refresh(self) -> None:
        """Recompute statuses and redraw in place; the selection is kept."""
        clear_template_cache()
        self.summary = compute_statuses(relink=True)
        self._rebuild_list()

    def stage_status(self) -> StageStatus:
        # Off screen the list may be stale (a template chosen on 4. Diagrams):
        # count again without touching the list; on screen, refresh() keeps it.
        summary = self.summary if self.isVisible() else compute_statuses(relink=False)
        if summary.is_empty:
            return StageStatus("none", S.STATUS_WAITING)
        needs = len(summary.needs)
        if needs:
            new = len(summary.new_needing_template)
            if new and new == needs:
                return StageStatus(
                    "warning", S.STATUS_NEW_NEEDS_TEMPLATE.format(count=new)
                )
            if needs == 1:
                return StageStatus("warning", S.STATUS_NEED_TEMPLATE_ONE)
            return StageStatus("warning", S.STATUS_NEED_TEMPLATE.format(count=needs))
        ready = len(summary.ready)
        if ready == 1:
            return StageStatus("ok", S.STATUS_ONE_READY)
        if ready:
            return StageStatus("ok", S.STATUS_ALL_READY.format(count=ready))
        if summary.no_diagram:
            return StageStatus("none", S.STATUS_NO_DIAGRAMS)
        return StageStatus("none", S.STATUS_NONE)

    def next_action(self) -> NextAction | None:
        """While controllers need a template the primary is "Choose N templates"
        (the picker opens for the first one); otherwise the next stage."""
        if self.summary.is_empty:
            return None
        needs = len(self.summary.needs)
        if needs:
            return NextAction(
                S.CHOOSE_N_TEMPLATES.format(
                    count=needs, templates=S.plural(needs, S.TEMPLATES)
                ),
                self.choose_first_needing,
                tooltip=S.CHOOSE_N_TEMPLATES_TIP,
            )
        return self._next_stage_action()

    def secondary_action(self) -> NextAction | None:
        """Nothing is ever locked: with templates still to choose, the way on."""
        if self.summary.is_empty or not self.summary.needs:
            return None
        if not self.summary.ready:
            return NextAction(
                S.SKIP_TO_BINDINGS, lambda: self.request_stage.emit(STAGE_BINDINGS, {})
            )
        return self._next_stage_action()

    def _next_stage_action(self) -> NextAction:
        from joystick_diagrams.ui.stage_shell import is_first_run_done

        if not is_first_run_done():
            return NextAction(
                S.NEXT_BINDINGS, lambda: self.request_stage.emit(STAGE_BINDINGS, {})
            )
        return NextAction(
            S.NEXT_DIAGRAMS, lambda: self.request_stage.emit(STAGE_DIAGRAMS, {})
        )

    def handle_request(self, payload: dict) -> None:
        guid = payload.get(PAYLOAD_DEVICE_GUID)
        if guid:
            self.select_guid(guid)
        if payload.get("action") == "choose_template" and guid:
            QTimer.singleShot(0, lambda g=guid: self.choose_template_for(g))

    navigate = handle_request

    def on_read_finished(self, _outcome: Any) -> None:
        pass  # the shell calls refresh() right after

    # ── List ──

    def _rebuild_list(self) -> None:
        summary = self.summary
        self.stack.setCurrentIndex(0 if summary.is_empty else 1)
        if summary.is_empty:
            self._selected_guid = None
            return
        if summary.needs:
            self.subtitle_label.setText(S.SUBTITLE_CHOOSE)
        elif summary.ready:
            self.subtitle_label.setText(S.SUBTITLE_ALL_SET)
        else:
            self.subtitle_label.setText(S.SUBTITLE_NONE)

        previous = self._selected_guid
        expanded = {
            self.tree.topLevelItem(i).data(0, ROLE_GROUP): self.tree.topLevelItem(
                i
            ).isExpanded()
            for i in range(self.tree.topLevelItemCount())
        }
        self.tree.blockSignals(True)
        self.tree.clear()
        self._rows = {}
        for group in GROUP_ORDER:
            guids = summary.guids_in(group)
            if not guids and group != GROUP_READY:
                continue
            header = QTreeWidgetItem(
                [S.GROUP_COUNT.format(group=GROUP_TITLES[group], count=len(guids))]
            )
            header.setData(0, ROLE_GROUP, group)
            header.setFlags(Qt.ItemFlag.ItemIsEnabled)
            font = header.font(0)
            font.setBold(True)
            header.setFont(0, font)
            self.tree.addTopLevelItem(header)
            for guid in guids:
                info = summary.statuses[guid]
                item = QTreeWidgetItem([""])
                item.setData(0, ROLE_GUID, guid)
                item.setSizeHint(0, QSize(0, 44))
                header.addChild(item)
                text = row_status_text(guid, info, summary.statuses)
                self.tree.setItemWidget(
                    item,
                    0,
                    ControllerRow(guid, info, text, show_new=summary.is_new(guid)),
                )
                self._rows[guid] = item
            header.setExpanded(expanded.get(group, group not in GROUP_COLLAPSED))
        self.tree.blockSignals(False)

        target = previous if previous in self._rows else None
        if target is None:
            ordered = (
                summary.needs + summary.ready + summary.no_diagram + summary.not_seen
            )
            target = ordered[0] if ordered else None
        if target is not None:
            self.select_guid(target, force=True)
        else:
            self._show_detail(None)

    def row_text(self, guid: str) -> str | None:
        item = self._rows.get(guid)
        widget = self.tree.itemWidget(item, 0) if item is not None else None
        return widget.status_label.text() if isinstance(widget, ControllerRow) else None

    def group_guids(self, group: str) -> list[str]:
        for i in range(self.tree.topLevelItemCount()):
            header = self.tree.topLevelItem(i)
            if header.data(0, ROLE_GROUP) == group:
                return [
                    header.child(j).data(0, ROLE_GUID)
                    for j in range(header.childCount())
                ]
        return []

    def is_group_expanded(self, group: str) -> bool:
        for i in range(self.tree.topLevelItemCount()):
            header = self.tree.topLevelItem(i)
            if header.data(0, ROLE_GROUP) == group:
                return header.isExpanded()
        return False

    def select_guid(self, guid: str, force: bool = False) -> bool:
        item = self._rows.get(guid)
        if item is None:
            return False
        parent = item.parent()
        if parent is not None and not parent.isExpanded():
            parent.setExpanded(True)
        if self.tree.currentItem() is item and force:
            self._show_detail(guid)
        else:
            self.tree.setCurrentItem(item)
        self.tree.scrollToItem(item)
        return True

    def _on_current_changed(
        self, current: QTreeWidgetItem | None, _previous=None
    ) -> None:
        guid = current.data(0, ROLE_GUID) if current is not None else None
        if guid is None:
            return
        self._show_detail(guid)

    # ── Detail ──

    @property
    def selected_guid(self) -> str | None:
        return self._selected_guid

    def _show_detail(self, guid: str | None) -> None:
        self._selected_guid = guid
        info = self.summary.statuses.get(guid) if guid else None
        if info is None:
            self.detail.hide()
            self.no_selection.show()
            return
        self.no_selection.hide()
        self.detail.show()
        self.detail_name.setText(info.name or guid)
        self._fill_template_section(guid, info)
        self._fill_diagram_row(info)
        self.used_in.setText(used_in_text(info))
        self._fill_more(guid, info)

    def _set_section_state(self, state: str) -> None:
        self.template_section.setProperty("state", state)
        self.template_section.style().unpolish(self.template_section)
        self.template_section.style().polish(self.template_section)

    def _set_fit_state(self, state: str) -> None:
        self.fit_line.setProperty("state", state)
        self.fit_line.style().unpolish(self.fit_line)
        self.fit_line.style().polish(self.fit_line)

    def _fill_template_section(self, guid: str, info: StatusInfo) -> None:
        has_template = (
            bool(info.template_path) and info.state is not DeviceStatus.NEEDS_TEMPLATE
        )
        usable = info.state.exports or (
            self.summary.snapshot and info.state is DeviceStatus.READY
        )
        self.missing_list.hide()
        self.missing_toggle.hide()
        self.choose_button.setText(
            S.CHANGE_TEMPLATE if has_template else S.CHOOSE_TEMPLATE
        )
        self.choose_button.setObjectName("ctrlAction" if usable else "ctrlPrimary")
        self.choose_button.style().unpolish(self.choose_button)
        self.choose_button.style().polish(self.choose_button)
        self.preview_button.setVisible(usable)
        self.edit_layout_button.setVisible(usable)
        self.view_bindings_button.setVisible(info.profile_count > 0 or usable)
        self.preview_button.setEnabled(info.state.exports)

        if info.state is DeviceStatus.NEEDS_TEMPLATE or not has_template:
            self._set_section_state("warning")
            self.template_name.setText(S.TEMPLATE_NONE)
            self.template_name.setObjectName("fitLine")
            self.template_source.setText("")
            self.fit_line.setText("")
            self._show_placeholder_thumb()
            self._restyle(self.template_name)
            return
        self.template_name.setObjectName("templateName")
        self._restyle(self.template_name)
        name = template_display_name(info)
        if info.state is DeviceStatus.TEMPLATE_MISSING:
            self._set_section_state("warning")
            text = (
                S.TEMPLATE_UNREADABLE
                if info.reason == "template_unreadable"
                else S.TEMPLATE_MISSING
            )
            self.template_name.setText(text.format(name=info.template_name or name))
            self.template_source.setText("")
            self.fit_line.setText("")
            self._show_placeholder_thumb()
            return
        self._set_section_state(
            "warning" if info.state is DeviceStatus.READY_WITH_GAPS else "ok"
        )
        self.template_name.setText(name)
        catalogue_info = None
        try:
            catalogue_info = template_catalog.info_for_path(Path(info.template_path))
        except Exception:  # noqa: BLE001
            catalogue_info = None
        parts = source_parts(catalogue_info)
        self.template_source.setText(" · ".join(parts))
        self._fill_fit(guid, info, catalogue_info)
        if catalogue_info is not None:
            self._start_thumbnail(catalogue_info)
        else:
            self._show_placeholder_thumb()

    def _fill_fit(self, guid: str, info: StatusInfo, catalogue_info: Any) -> None:
        if self.summary.snapshot or catalogue_info is None:
            self.fit_line.setText("")
            return
        from joystick_diagrams.ui.template_picker import bound_devices_for

        try:
            result = template_catalog.fit(catalogue_info, bound_devices_for(guid))
        except Exception as error:  # noqa: BLE001
            _logger.debug(f"Fit failed for {guid}: {error}")
            self.fit_line.setText("")
            return
        self.fit_line.setText(template_catalog.fit_text(result))
        self._set_fit_state(
            "ok" if result.fits_all else "warning" if result.total_bound else ""
        )
        if result.missing:
            count = len(result.missing)
            self.missing_toggle.setText(
                S.MISSING_CONTROLS.format(
                    count=count, controls=S.plural(count, S.CONTROLS)
                )
            )
            self.missing_list.setText(", ".join(result.missing))
            self.missing_toggle.show()

    def _toggle_missing(self) -> None:
        self.missing_list.setVisible(not self.missing_list.isVisible())

    @staticmethod
    def _restyle(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _show_placeholder_thumb(self) -> None:
        self._thumb_key = None
        self.thumbnail.setPixmap(
            qta.icon("fa5s.gamepad", color="#5F6368").pixmap(QSize(56, 56))
        )

    def _start_thumbnail(self, info: Any) -> None:
        from joystick_diagrams.ui.template_picker import ThumbnailRunnable

        self._thumb_key = info.key
        self.thumbnail.setPixmap(
            qta.icon("fa5s.sync", color="#5F6368").pixmap(QSize(22, 22))
        )
        self._pool.start(ThumbnailRunnable(info, self._thumb_signals, THUMB_WIDTH * 2))

    def _on_thumb_ready(self, key: str, path: str) -> None:
        if key != self._thumb_key:
            return
        pixmap = QPixmap(path) if path else QPixmap()
        if pixmap.isNull():
            self._show_placeholder_thumb()
            return
        self.thumbnail.setPixmap(
            pixmap.scaled(
                self.thumbnail.width() - 8,
                self.thumbnail.height() - 8,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _fill_diagram_row(self, info: StatusInfo) -> None:
        no_diagram = info.state in (DeviceStatus.NO_DIAGRAM, DeviceStatus.MERGED)
        self.make_diagram.blockSignals(True)
        self.make_diagram.setChecked(not no_diagram)
        self.make_diagram.blockSignals(False)
        self.make_diagram.setEnabled(info.state is not DeviceStatus.MERGED)
        reason = ""
        if info.state is DeviceStatus.MERGED:
            reason = (
                reason_text(
                    "merged_into", merged_name=merged_name(info, self.summary.statuses)
                )
                or ""
            )
        elif no_diagram:
            reason = reason_text(info.reason, info.template_name) or ""
        elif info.kind_source == "user":
            reason = S.REASON_SET_BY_YOU
        else:
            kind = self.appState.device_service.kind(self._selected_guid or "")
            if kind is not None and kind.is_user:
                reason = S.REASON_SET_BY_YOU
        self.reason_label.setText(f"· {reason}" if reason else "")

    def _fill_more(self, guid: str, info: StatusInfo) -> None:
        service = self.appState.device_service
        original = self._original_name(guid) or info.name or guid
        self.name_edit.blockSignals(True)
        self.name_edit.setText(service.get_custom_name(guid) or "")
        self.name_edit.setPlaceholderText(original)
        self.name_edit.blockSignals(False)
        self.name_reset.setEnabled(service.get_custom_name(guid) is not None)
        self.id_label.setText(guid)
        self.same_problem.hide()

        self.same_combo.blockSignals(True)
        self.same_combo.clear()
        self.same_combo.addItem(S.SAME_CONTROLLER_NONE, None)
        names: dict[str, int] = {}
        others = [
            (g, i.name or g)
            for g, i in self.summary.statuses.items()
            if g != guid and group_of(i) is not None
        ]
        for _g, name in others:
            names[name] = names.get(name, 0) + 1
        for other, name in sorted(others, key=lambda item: item[1].casefold()):
            label = f"{name}  [{other[:8]}]" if names[name] > 1 else name
            self.same_combo.addItem(label, other)
        target = self.appState.device_alias_service.get_all_aliases().get(guid)
        if target:
            index = self.same_combo.findData(target)
            if index >= 0:
                self.same_combo.setCurrentIndex(index)
        self.same_combo.blockSignals(False)

    def _original_name(self, guid: str) -> str | None:
        facts = collect_device_facts(self.appState.profile_wrappers).get(guid)
        if facts is not None and facts.name:
            return facts.name
        row = self.appState.device_service.row(guid)
        return row.name if row else None

    def _toggle_more(self, shown: bool) -> None:
        self.more.setVisible(shown)
        self.more_button.setArrowType(
            Qt.ArrowType.DownArrow if shown else Qt.ArrowType.RightArrow
        )

    # ── Actions ──

    def _changed(self, reprocess: bool = False) -> None:
        if reprocess:
            self.appState.process_profiles_from_collections()
            main_window = self.appState.main_window
            invalidate = getattr(main_window, "_invalidate_data_pages", None)
            if callable(invalidate):
                invalidate()  # refreshes this page too
                self.state_changed.emit()
                return
        self.refresh()
        self.state_changed.emit()

    def choose_template_for_selected(self) -> None:
        if self._selected_guid:
            self.choose_template_for(self._selected_guid)

    def choose_template_for(self, guid: str) -> bool:
        from joystick_diagrams.ui.template_picker import choose_template

        info = self.summary.statuses.get(guid)
        result = choose_template(
            self,
            guid,
            device_name=info.name if info else None,
            profile_count=info.profile_count if info else None,
        )
        if result is None:
            return False
        was_needed = guid in self.summary.needs
        self.refresh()
        self.state_changed.emit()
        if was_needed and not result.removed:
            remaining = [g for g in self.summary.needs if g != guid]
            if remaining:
                self.select_guid(remaining[0])
                self.choose_button.setFocus()
        return True

    def choose_first_needing(self) -> None:
        needs = self.summary.needs
        if needs:
            self.select_guid(needs[0])
            self.choose_template_for(needs[0])

    def _on_make_diagram_toggled(self, checked: bool) -> None:
        guid = self._selected_guid
        if not guid:
            return
        info = self.summary.statuses.get(guid)
        self.appState.device_service.set_make_diagram(
            guid, checked, (info.name if info else None) or self._original_name(guid)
        )
        self._changed()

    def _on_name_edited(self) -> None:
        guid = self._selected_guid
        if not guid:
            return
        text = self.name_edit.text().strip()
        current = self.appState.device_service.get_custom_name(guid)
        if (text or None) == current:
            return
        self.appState.device_service.set_custom_name(guid, text or None)
        self._changed()

    def _on_name_reset(self) -> None:
        guid = self._selected_guid
        if not guid:
            return
        self.appState.device_service.set_custom_name(guid, None)
        self._changed()

    def _on_same_changed(self, _index: int) -> None:
        guid = self._selected_guid
        if not guid:
            return
        target = self.same_combo.currentData(Qt.ItemDataRole.UserRole)
        aliases = self.appState.device_alias_service
        if target is None:
            aliases.remove_alias(guid)
        else:
            try:
                aliases.set_alias(guid, target)
            except ValueError as error:
                _logger.info(f"Same controller as… refused: {error}")
                self.same_problem.setText(S.SAME_CONTROLLER_PROBLEM)
                self.same_problem.show()
                self.same_combo.blockSignals(True)
                self.same_combo.setCurrentIndex(0)
                self.same_combo.blockSignals(False)
                return
        self._changed(reprocess=True)

    def _copy_id(self) -> None:
        if self._selected_guid:
            QApplication.clipboard().setText(self._selected_guid)
            self.copy_id.setText(S.COPIED)
            QTimer.singleShot(
                1500, self.copy_id, lambda: self.copy_id.setText(S.COPY_ID)
            )

    def _edit_layout(self) -> None:
        if self._selected_guid:
            self.request_stage.emit(
                STAGE_DIAGRAMS,
                {
                    PAYLOAD_DEVICE_GUID: self._selected_guid,
                    PAYLOAD_SECTION: SECTION_LAYOUT,
                },
            )

    def _view_bindings(self) -> None:
        if self._selected_guid:
            self.request_stage.emit(
                STAGE_BINDINGS, {PAYLOAD_DEVICE_GUID: self._selected_guid}
            )

    def export_devices_for(self, guid: str) -> list[Any]:
        from joystick_diagrams.ui.device_setup_controller import (
            convert_profile_wrappers_to_export_devices,
            setup_export_devices,
        )

        devices = [
            d
            for d in convert_profile_wrappers_to_export_devices(
                self.appState.profile_wrappers
            )
            if d.device_id == guid
        ]
        setup_export_devices(devices)
        return [d for d in devices if d.template is not None]

    def _open_preview(self) -> None:
        guid = self._selected_guid
        if not guid:
            return
        devices = self.export_devices_for(guid)
        if not devices:
            return
        from joystick_diagrams.ui.preview_window import PreviewWindow

        window = PreviewWindow(devices, devices[0], self)
        window.edit_layout_requested.connect(
            lambda device_id: self.request_stage.emit(
                STAGE_DIAGRAMS,
                {PAYLOAD_DEVICE_GUID: device_id, PAYLOAD_SECTION: SECTION_LAYOUT},
            )
        )
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._preview_window = window
        window.show()


__all__ = [
    "ControllerSummary",
    "ControllersPage",
    "compute_statuses",
    "group_of",
    "row_status_text",
    "snapshot_statuses",
]

if __name__ == "__main__":
    pass
