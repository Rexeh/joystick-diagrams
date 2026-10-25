"""The Export list (4. Diagrams › Export, journey boards J08, J12, J13).

``build_export_model`` turns the controller statuses (``device_status``), the
export devices and the pages into rows; ``ExportList`` draws them.

- A **controller row** per Ready controller (expands to its profiles), status
  "✔ Ready" or "⚠ 3 bindings won't show · Why?". Every profile is ticked by
  default; ticks are remembered (``workflow_settings``) under
  ``device:<guid>|<profile_key>``.
- A **page row** per combined page, "▣ <page> · page · <size>", expanding to the
  profiles the page is made for (``export.page_profiles``); key
  ``page:<page_id>|<profile_key>``. A page whose member has no template goes to
  "Not included" instead.
- A page with "Export them only on this page" ticked (``export_members_separately``
  False) *covers* its controllers' profiles that it renders (its own profile
  rule, ``render.compose.page_profile_plan``): those profile rows are unticked,
  disabled, marked "(on <page> page)" and never exported, counted or ticked,
  whatever ticks are remembered (the remembered tick is kept, not overwritten,
  so it comes back when the page goes or its flag/rule changes). The controller's
  other profiles stay ordinary rows; a controller whose every profile is covered
  says "(on <page> page)" itself. On several pages, the union applies.
- "Not included" lists controllers without a usable template; "No diagram"
  lists the controllers that get none, with the reason.

There is no template assignment here: no double-click-to-assign, no Set/Clear
Template. Right-click offers Preview… and Edit layout ›.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams import workflow_settings
from joystick_diagrams.db import db_settings
from joystick_diagrams.ui import strings_diagrams as S

_logger = logging.getLogger(__name__)

ROW_KEY_ROLE = Qt.ItemDataRole.UserRole
TICK_KEY_ROLE = Qt.ItemDataRole.UserRole + 1
PROFILE_ROLE = Qt.ItemDataRole.UserRole + 2

KIND_CONTROLLER = "controller"
KIND_PAGE = "page"
LAST_EXPORT_SETTING_KEY = "export_last_ticked"

COLUMN_NAME = 0
COLUMN_PROFILES = 1
COLUMN_STATUS = 2

AMBER = QColor("#F59E0B")
GREEN = QColor("#34D399")
MUTED = QColor("#9AA0A6")
LINK_STYLE = "color: #8AB4F8; text-decoration: none;"


# ── Model ──


@dataclass
class ProfileEntry:
    tick_key: str
    profile_key: str
    profile_name: str
    game: str
    wrapper: Any
    export_device: Any = None  # controller rows
    gaps: int = 0  # controls this profile binds that have no box
    default_ticked: bool = True
    covered_by: list[str] = field(default_factory=list)  # pages exporting it
    drawn_empty: list[str] = field(default_factory=list)  # pages: no bindings here


@dataclass
class ExportRow:
    key: str
    kind: str
    name: str
    guid: str | None = None
    page: Any = None
    status: Any = None
    profiles: list[ProfileEntry] = field(default_factory=list)
    on_page: str | None = None  # the first page, when every profile is covered
    on_pages: list[str] = field(default_factory=list)  # all of those pages
    size_text: str = ""

    @property
    def tickable(self) -> list[ProfileEntry]:
        return [p for p in self.profiles if not p.covered_by]

    @property
    def gaps(self) -> int:
        return len(getattr(self.status, "missing_controls", None) or [])

    @property
    def missing_controls(self) -> list[str]:
        return list(getattr(self.status, "missing_controls", None) or [])


@dataclass
class NotIncluded:
    guid: str
    name: str
    text: str
    page_id: str | None = None


@dataclass
class ExportModel:
    rows: list[ExportRow] = field(default_factory=list)
    not_included: list[NotIncluded] = field(default_factory=list)
    no_diagram: list[tuple[str, str, str]] = field(
        default_factory=list
    )  # guid, name, reason
    games: list[str] = field(default_factory=list)

    def row(self, key: str) -> ExportRow | None:
        return next((r for r in self.rows if r.key == key), None)

    @property
    def tick_keys(self) -> list[str]:
        """The keys that can be ticked (rows covered by a page are left out)."""
        return [p.tick_key for r in self.rows for p in r.tickable]

    @property
    def covered_keys(self) -> set[str]:
        return {p.tick_key for r in self.rows for p in r.profiles if p.covered_by}

    def default_ticks(self) -> dict[str, bool]:
        return {p.tick_key: p.default_ticked for r in self.rows for p in r.profiles}


def controller_key(guid: str) -> str:
    return f"device:{guid}"


def page_key(page_id: str) -> str:
    return f"page:{page_id}"


def tick_key(row_key: str, profile_key: str) -> str:
    return f"{row_key}|{profile_key}"


def _game(wrapper: Any) -> str:
    origin = getattr(wrapper, "profile_origin", None)
    return str(getattr(origin, "name", "") or "")


def page_size_text(page: Any) -> str:
    """ "A4 landscape", "Kneeboard 5.5 × 8.5 in portrait", "Fit to content"."""
    from joystick_diagrams.render.page import (
        SIZE_PRESET_LABELS,
        Arrangement,
        Orientation,
        SizePreset,
    )

    if page.size_preset is SizePreset.CUSTOM:
        size = f"{page.width_mm or 0:g} × {page.height_mm or 0:g} mm"
    else:
        size = SIZE_PRESET_LABELS.get(page.size_preset, str(page.size_preset))
    if page.size_preset is SizePreset.FIT:
        return size
    orientation = page.orientation
    if orientation is Orientation.AUTO:
        orientation = {
            Arrangement.SIDE_BY_SIDE: Orientation.LANDSCAPE,
            Arrangement.STACKED: Orientation.PORTRAIT,
        }.get(page.arrangement, Orientation.AUTO)
    if orientation is Orientation.AUTO:
        return size
    word = (
        S.ORIENTATION_LANDSCAPE
        if orientation is Orientation.LANDSCAPE
        else S.ORIENTATION_PORTRAIT
    )
    return S.PAGE_SIZE_ORIENTED.format(size=size, orientation=word)


def _profile_match_key(wrapper: Any) -> str:
    # The same key ``render.compose`` groups a page's profiles by.
    return str(
        getattr(wrapper, "profile_key", None) or getattr(wrapper, "profile_name", "")
    )


def covered_profiles(
    pages: Iterable[Any], export_devices: Iterable[Any]
) -> dict[str, dict[str, list[str]]]:
    """``{guid: {profile_key: [page names]}}``: the controllers' profiles that a
    page exporting "only on this page" renders, so they aren't exported on their
    own. Pages are taken in order; a controller on two pages gets the union."""
    from joystick_diagrams.render.compose import page_profile_plan

    export_devices = list(export_devices)
    covered: dict[str, dict[str, list[str]]] = {}
    for page in pages:
        if page.export_members_separately:
            continue
        keys = [
            _profile_match_key(entry.wrapper)
            for entry in page_profile_plan(page, export_devices)
        ]
        for guid in page.member_guids:
            by_profile = covered.setdefault(guid, {})
            for key in keys:
                names = by_profile.setdefault(key, [])
                if page.name not in names:
                    names.append(page.name)
    return covered


def on_page_text(page_names: list[str]) -> str:
    """ "(on <page> page)", or "(on <page> page +1 more)" for several pages."""
    if len(page_names) > 1:
        return S.ROW_ON_PAGES.format(page=page_names[0], more=len(page_names) - 1)
    return S.ROW_ON_PAGE.format(page=page_names[0])


def on_page_tooltip(page_names: list[str]) -> str:
    return S.ROW_ON_PAGE_TIP.format(page=page_names[0])


def _page_row(
    page: Any,
    statuses: dict[str, Any],
    export_devices: list[Any],
    page_profiles: Callable[[Any, list[Any]], list[Any]] | None,
) -> ExportRow | NotIncluded | None:
    """A page's row, its "Not included" line when a member needs a template, or
    ``None`` when a member isn't in the latest bindings (such as before the launch
    read finishes): the page waits quietly instead of blaming a template."""
    from joystick_diagrams.device_status import DeviceStatus

    waiting = (DeviceStatus.NEEDS_TEMPLATE, DeviceStatus.TEMPLATE_MISSING)
    blocking = [
        guid
        for guid in page.member_guids
        if guid not in statuses or not statuses[guid].state.exports
    ]
    needs = [g for g in blocking if g in statuses and statuses[g].state in waiting]
    if blocking and not needs:
        return None
    if needs:
        guid = needs[0]
        info = statuses[guid]
        name = info.name or guid
        return NotIncluded(
            guid,
            page.name,
            S.NOT_INCLUDED_PAGE.format(page=page.name, controller=name),
            page.page_id,
        )
    key = page_key(page.page_id)
    row = ExportRow(
        key, KIND_PAGE, page.name, page=page, size_text=page_size_text(page)
    )
    if page_profiles is None:
        return row
    from joystick_diagrams.render.compose import page_profile_plan

    # The page's own rule decides the profiles (default: every controller on it
    # has bindings there); under "any", the ones drawn empty are named.
    for entry in page_profile_plan(page, export_devices):
        wrapper = entry.wrapper
        row.profiles.append(
            ProfileEntry(
                tick_key(key, wrapper.profile_key),
                wrapper.profile_key,
                wrapper.profile_name,
                _game(wrapper),
                wrapper,
                drawn_empty=[
                    (statuses[g].name if g in statuses else None) or g
                    for g in entry.missing
                ],
            )
        )
    return row


def _controller_row(
    guid: str, info: Any, devices: list[Any], covered: dict[str, list[str]]
) -> ExportRow:
    key = controller_key(guid)
    row = ExportRow(key, KIND_CONTROLLER, info.name or guid, guid=guid, status=info)
    for export_device in devices:
        wrapper = export_device.profile_wrapper
        covered_by = list(covered.get(_profile_match_key(wrapper), []))
        row.profiles.append(
            ProfileEntry(
                tick_key(key, wrapper.profile_key),
                wrapper.profile_key,
                wrapper.profile_name,
                _game(wrapper),
                wrapper,
                export_device=export_device,
                gaps=len(getattr(export_device, "errors", None) or ()),
                default_ticked=not covered_by,
                covered_by=covered_by,
            )
        )
    if row.profiles and not row.tickable:
        pages: list[str] = []
        for entry in row.profiles:
            pages.extend(n for n in entry.covered_by if n not in pages)
        row.on_pages = pages
        row.on_page = pages[0]
    return row


def _not_included_text(info: Any, name: str) -> str:
    from joystick_diagrams.device_status import DeviceStatus

    if info.state is DeviceStatus.TEMPLATE_MISSING and info.template_name:
        return S.NOT_INCLUDED_MISSING.format(
            controller=name, template=info.template_name
        )
    return S.NOT_INCLUDED.format(controller=name)


def build_export_model(
    export_devices: Iterable[Any],
    statuses: dict[str, Any],
    pages: Iterable[Any] = (),
    page_profiles: Callable[[Any, list[Any]], list[Any]] | None = None,
) -> ExportModel:
    """Rows, "Not included" and "No diagram" from the statuses (pure; no Qt).

    Pages come first (they are what the player asked for), then controllers by name.
    """
    from joystick_diagrams.device_status import DeviceStatus

    export_devices = list(export_devices)
    pages = list(pages)
    model = ExportModel()
    by_guid: dict[str, list[Any]] = {}
    for export_device in export_devices:
        by_guid.setdefault(export_device.device_id, []).append(export_device)
    exported_pages = []
    for page in pages:
        result = _page_row(page, statuses, export_devices, page_profiles)
        if result is None:
            continue
        if isinstance(result, NotIncluded):
            model.not_included.append(result)
        else:
            model.rows.append(result)
            exported_pages.append(page)
    # Only a page that is in the list covers its controllers' rows: one that is
    # "Not included" (or waiting for the read) exports nothing in their place.
    covered = covered_profiles(exported_pages, export_devices)

    controller_rows: list[ExportRow] = []
    waiting = (DeviceStatus.NEEDS_TEMPLATE, DeviceStatus.TEMPLATE_MISSING)
    for guid, info in statuses.items():
        name = info.name or guid
        if info.state.exports:
            row = _controller_row(
                guid, info, by_guid.get(guid, []), covered.get(guid, {})
            )
            if row.profiles:
                controller_rows.append(row)
        elif info.state in waiting:
            model.not_included.append(
                NotIncluded(guid, name, _not_included_text(info, name))
            )
        elif info.state is DeviceStatus.NO_DIAGRAM:
            reason = info.reason_text or ""
            model.no_diagram.append((guid, name, reason[:1].lower() + reason[1:]))
    controller_rows.sort(key=lambda r: r.name.casefold())
    model.rows.extend(controller_rows)
    model.not_included.sort(key=lambda n: n.name.casefold())
    model.no_diagram.sort(key=lambda n: n[1].casefold())
    model.games = sorted({p.game for r in model.rows for p in r.profiles if p.game})
    return model


def load_ticks(model: ExportModel) -> dict[str, bool]:
    """The remembered tick for every tickable row of ``model`` (defaults for new
    rows). Rows covered by a page are left out: their remembered tick stays in
    the settings, untouched, for when the page no longer covers them."""
    stored = workflow_settings.get_export_ticks()
    covered = model.covered_keys
    return {
        key: stored.get(key, default)
        for key, default in model.default_ticks().items()
        if key not in covered
    }


def last_export_keys() -> set[str]:
    raw = db_settings.get_setting(LAST_EXPORT_SETTING_KEY)
    if not raw:
        return set()
    try:
        data = json.loads(raw)
    except ValueError:
        return set()
    return {str(k) for k in data} if isinstance(data, list) else set()


def store_last_export_keys(keys: Iterable[str]) -> None:
    db_settings.add_update_setting_value(
        LAST_EXPORT_SETTING_KEY, json.dumps(sorted(set(keys)))
    )


# ── Widget ──


class ExportList(QWidget):
    """The tickable Export table (Controller · Profiles · Status)."""

    ticks_changed = Signal(int)  # number of ticked diagrams
    why_requested = Signal(str)  # controller guid
    preview_requested = Signal(object)  # ExportDevice
    edit_layout_requested = Signal(str)  # controller guid
    page_layout_requested = Signal(str)  # page id

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.model = ExportModel()
        self._ticks: dict[str, bool] = {}
        self._loading = False
        self._game_filter = ""
        self._search = ""
        self._locked = False
        self._persist_timer = QTimer(self)
        self._persist_timer.setSingleShot(True)
        self._persist_timer.setInterval(0)
        self._persist_timer.timeout.connect(self._persist)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.treeWidget = QTreeWidget()
        self.treeWidget.setProperty("class", "device-tree")
        self.treeWidget.setColumnCount(3)
        self.treeWidget.setHeaderLabels(
            [S.COLUMN_CONTROLLER, S.COLUMN_PROFILES, S.COLUMN_STATUS]
        )
        header = self.treeWidget.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(COLUMN_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            COLUMN_PROFILES, QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(COLUMN_STATUS, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(COLUMN_STATUS, 260)
        self.treeWidget.setIconSize(QSize(16, 16))
        self.treeWidget.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.treeWidget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.treeWidget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.treeWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.treeWidget.customContextMenuRequested.connect(self._show_context_menu)
        self.treeWidget.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.treeWidget)

    # ── Building ──

    def set_model(self, model: ExportModel, ticks: dict[str, bool] | None = None):
        expanded = {
            self.treeWidget.topLevelItem(i).data(COLUMN_NAME, ROW_KEY_ROLE)
            for i in range(self.treeWidget.topLevelItemCount())
            if self.treeWidget.topLevelItem(i).isExpanded()
        }
        self.model = model
        covered = model.covered_keys
        self._ticks = {
            key: value
            for key, value in (
                ticks if ticks is not None else load_ticks(model)
            ).items()
            if key not in covered
        }
        self._loading = True
        try:
            self.treeWidget.clear()
            for row in model.rows:
                item = self._row_item(row)
                self.treeWidget.addTopLevelItem(item)
                if row.key in expanded:
                    item.setExpanded(True)
                self._add_status_widget(item, row)
        finally:
            self._loading = False
        self._apply_filter()
        self._update_counts()

    def _row_item(self, row: ExportRow) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        item.setData(COLUMN_NAME, ROW_KEY_ROLE, row.key)
        if row.kind == KIND_PAGE:
            count = len(row.profiles)
            item.setText(
                COLUMN_NAME,
                S.PAGE_ROW_NAME.format(
                    name=row.name,
                    size=row.size_text,
                    profiles=S.counted(count, S.PROFILES),
                ),
            )
        else:
            item.setText(COLUMN_NAME, row.name)
            template = getattr(row.status, "template_name", None)
            if template:
                item.setToolTip(
                    COLUMN_NAME, S.ROW_TEMPLATE_TIP.format(template=template)
                )
        self._set_row_flags(item, row)
        for entry in row.profiles:
            self._add_profile_child(item, row, entry)
        if not row.profiles:
            item.setCheckState(COLUMN_NAME, Qt.CheckState.Unchecked)
        elif len(row.tickable) != len(row.profiles):
            self._sync_row_check(item)
        return item

    @staticmethod
    def _set_row_flags(item: QTreeWidgetItem, row: ExportRow) -> None:
        if not row.profiles or len(row.tickable) == len(row.profiles):
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsAutoTristate
            )
        else:
            # Some profiles are covered by a page: Qt's auto-tristate would tick
            # them along with the row, so the row's box follows only the
            # tickable ones (``_sync_row_check``); none left → not clickable.
            flags = item.flags() & ~Qt.ItemFlag.ItemIsAutoTristate
            if row.tickable:
                flags |= Qt.ItemFlag.ItemIsUserCheckable
            else:
                flags &= ~Qt.ItemFlag.ItemIsUserCheckable
            item.setFlags(flags)

    def _add_profile_child(
        self, item: QTreeWidgetItem, row: ExportRow, entry: ProfileEntry
    ) -> None:
        child = QTreeWidgetItem(item)
        child.setData(COLUMN_NAME, ROW_KEY_ROLE, row.key)
        child.setData(COLUMN_NAME, TICK_KEY_ROLE, entry.tick_key)
        child.setData(COLUMN_NAME, PROFILE_ROLE, entry)
        child.setText(COLUMN_NAME, f"{entry.game} / {entry.profile_name}")
        icon = getattr(getattr(entry.wrapper, "profile_origin", None), "icon", "")
        if isinstance(icon, str) and icon:
            child.setIcon(COLUMN_NAME, QIcon(icon))
        if entry.covered_by:
            child.setFlags(
                child.flags()
                & ~Qt.ItemFlag.ItemIsUserCheckable
                & ~Qt.ItemFlag.ItemIsEnabled
            )
            child.setCheckState(COLUMN_NAME, Qt.CheckState.Unchecked)
            child.setText(COLUMN_STATUS, on_page_text(entry.covered_by))
            child.setForeground(COLUMN_STATUS, QBrush(MUTED))
            tip = on_page_tooltip(entry.covered_by)
            child.setToolTip(COLUMN_NAME, tip)
            child.setToolTip(COLUMN_STATUS, tip)
            return
        child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        child.setCheckState(
            COLUMN_NAME,
            Qt.CheckState.Checked
            if self._ticks.get(entry.tick_key, entry.default_ticked)
            else Qt.CheckState.Unchecked,
        )
        if entry.gaps:
            child.setText(COLUMN_STATUS, S.ROW_PROFILE_GAPS.format(count=entry.gaps))
            child.setForeground(COLUMN_STATUS, QBrush(AMBER))
        elif entry.drawn_empty:
            child.setText(
                COLUMN_STATUS,
                S.ROW_DRAWN_EMPTY.format(controllers=S.join_and(entry.drawn_empty)),
            )
            child.setForeground(COLUMN_STATUS, QBrush(AMBER))

    def _sync_row_check(self, item: QTreeWidgetItem) -> None:
        """A row with covered profiles: its box from the tickable profiles only."""
        states = [
            item.child(j).checkState(COLUMN_NAME)
            for j in range(item.childCount())
            if not self._is_covered_item(item.child(j))
        ]
        if states and all(s == Qt.CheckState.Checked for s in states):
            state = Qt.CheckState.Checked
        elif any(s == Qt.CheckState.Checked for s in states):
            state = Qt.CheckState.PartiallyChecked
        else:
            state = Qt.CheckState.Unchecked
        loading, self._loading = self._loading, True
        try:
            item.setCheckState(COLUMN_NAME, state)
        finally:
            self._loading = loading

    @staticmethod
    def _is_covered_item(item: QTreeWidgetItem) -> bool:
        entry = item.data(COLUMN_NAME, PROFILE_ROLE)
        return bool(getattr(entry, "covered_by", None))

    def _is_manual_row(self, item: QTreeWidgetItem) -> bool:
        return not (item.flags() & Qt.ItemFlag.ItemIsAutoTristate) and any(
            self._is_covered_item(item.child(j)) for j in range(item.childCount())
        )

    def _add_status_widget(self, item: QTreeWidgetItem, row: ExportRow) -> None:
        """Status column: "✔ Ready", "⚠ 3 bindings won't show · Why?" or "(on X page)"."""
        if row.on_page:
            item.setText(COLUMN_STATUS, on_page_text(row.on_pages))
            item.setForeground(COLUMN_STATUS, QBrush(MUTED))
            item.setToolTip(COLUMN_STATUS, on_page_tooltip(row.on_pages))
            return
        gaps = row.gaps if row.kind == KIND_CONTROLLER else 0
        if not gaps:
            item.setText(COLUMN_STATUS, S.ROW_READY)
            item.setForeground(COLUMN_STATUS, QBrush(GREEN))
            return
        text = S.ROW_GAPS.format(count=gaps, bindings=S.plural(gaps, *S.BINDINGS))
        item.setText(COLUMN_STATUS, text)
        label = QLabel(
            f'<span style="color:#F59E0B">{text}</span> · '
            f'<a href="why" style="{LINK_STYLE}">{S.ROW_WHY}</a>'
        )
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setStyleSheet("background: transparent;")
        label.setAccessibleName(f"{text}. {S.ROW_WHY}")
        guid = row.guid or ""
        label.linkActivated.connect(lambda _link, g=guid: self.why_requested.emit(g))
        self.treeWidget.setItemWidget(item, COLUMN_STATUS, label)
        item.setText(COLUMN_STATUS, "")

    # ── Ticks ──

    def _row_ticked_count(self, row: ExportRow) -> int:
        return sum(1 for p in row.tickable if self._ticks.get(p.tick_key, False))

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._loading or column != COLUMN_NAME:
            return
        key = item.data(COLUMN_NAME, TICK_KEY_ROLE)
        if key is None:
            if self._is_manual_row(item):
                self._apply_row_check(item)
            return  # otherwise Qt propagates to the children, which arrive here
        if self._is_covered_item(item):
            # Never ticked: exported on its page instead.
            self._loading = True
            try:
                item.setCheckState(COLUMN_NAME, Qt.CheckState.Unchecked)
            finally:
                self._loading = False
            return
        self._ticks[key] = item.checkState(COLUMN_NAME) == Qt.CheckState.Checked
        parent = item.parent()
        if parent is not None and self._is_manual_row(parent):
            self._sync_row_check(parent)
        self._persist_timer.start()

    def _apply_row_check(self, item: QTreeWidgetItem) -> None:
        """The player ticked a row with covered profiles: its tickable ones follow."""
        ticked = item.checkState(COLUMN_NAME) != Qt.CheckState.Unchecked
        state = Qt.CheckState.Checked if ticked else Qt.CheckState.Unchecked
        self._loading = True
        try:
            for j in range(item.childCount()):
                child = item.child(j)
                if self._is_covered_item(child):
                    continue
                child.setCheckState(COLUMN_NAME, state)
                self._ticks[child.data(COLUMN_NAME, TICK_KEY_ROLE)] = ticked
        finally:
            self._loading = False
        self._sync_row_check(item)
        self._persist_timer.start()

    def _persist(self) -> None:
        stored = workflow_settings.get_export_ticks()
        stored.update(self._ticks)
        workflow_settings.set_export_ticks(stored)
        self._update_counts()

    def flush(self) -> None:
        """Write pending tick changes now (tests, before an export)."""
        if self._persist_timer.isActive():
            self._persist_timer.stop()
            self._persist()

    def _update_counts(self) -> None:
        for i in range(self.treeWidget.topLevelItemCount()):
            item = self.treeWidget.topLevelItem(i)
            row = self.model.row(item.data(COLUMN_NAME, ROW_KEY_ROLE))
            if row is None:
                continue
            ticked = self._row_ticked_count(row)
            count = len(row.profiles)
            # Always "ticked of total" so an unticked row reads "0 of 1", not
            # "1 profile": one format per column.
            text = S.ROW_PROFILES_TICKED.format(ticked=ticked, count=count)
            self._loading = True
            try:
                item.setText(COLUMN_PROFILES, text)
            finally:
                self._loading = False
        self.ticks_changed.emit(self.ticked_count())

    def ticks(self) -> dict[str, bool]:
        return dict(self._ticks)

    def ticked_keys(self) -> list[str]:
        return [k for k in self.model.tick_keys if self._ticks.get(k, False)]

    def ticked_count(self) -> int:
        return len(self.ticked_keys())

    def set_ticks(self, keys: Iterable[str] | None, visible_only: bool = True) -> None:
        """Tick exactly ``keys`` (``None``: every row) among the shown rows."""
        wanted = None if keys is None else set(keys)
        self._loading = True
        try:
            for item in self._profile_items():
                if visible_only and (item.isHidden() or item.parent().isHidden()):
                    continue
                if self._is_covered_item(item):
                    continue  # exported on its page; its remembered tick is kept
                key = item.data(COLUMN_NAME, TICK_KEY_ROLE)
                ticked = wanted is None or key in wanted
                self._ticks[key] = ticked
                item.setCheckState(
                    COLUMN_NAME,
                    Qt.CheckState.Checked if ticked else Qt.CheckState.Unchecked,
                )
            for i in range(self.treeWidget.topLevelItemCount()):
                root = self.treeWidget.topLevelItem(i)
                if self._is_manual_row(root):
                    self._sync_row_check(root)
        finally:
            self._loading = False
        self._persist()

    def tick_all(self) -> None:
        self.set_ticks(None)

    def tick_none(self) -> None:
        self.set_ticks(set())

    def tick_same_as_last(self) -> None:
        self.set_ticks(last_export_keys(), visible_only=False)

    def tick_row(self, row_key: str, ticked: bool = True) -> None:
        for item in self._profile_items():
            if item.data(COLUMN_NAME, ROW_KEY_ROLE) == row_key:
                if self._is_covered_item(item):
                    continue
                item.setCheckState(
                    COLUMN_NAME,
                    Qt.CheckState.Checked if ticked else Qt.CheckState.Unchecked,
                )
        self.flush()

    def _profile_items(self) -> list[QTreeWidgetItem]:
        items = []
        for i in range(self.treeWidget.topLevelItemCount()):
            root = self.treeWidget.topLevelItem(i)
            items.extend(root.child(j) for j in range(root.childCount()))
        return items

    def set_locked(self, locked: bool) -> None:
        """Ticks are locked while an export runs."""
        self._locked = locked
        self.treeWidget.setEnabled(not locked)

    # ── What to export ──

    def selected_export_devices(self) -> list[Any]:
        ticked = set(self.ticked_keys())
        return [
            p.export_device
            for r in self.model.rows
            if r.kind == KIND_CONTROLLER
            for p in r.profiles
            if p.tick_key in ticked and p.export_device is not None
        ]

    def selected_page_jobs(self) -> list[tuple[Any, Any]]:
        ticked = set(self.ticked_keys())
        return [
            (r.page, p.wrapper)
            for r in self.model.rows
            if r.kind == KIND_PAGE
            for p in r.profiles
            if p.tick_key in ticked
        ]

    def export_devices_for(self, guid: str) -> list[Any]:
        row = self.model.row(controller_key(guid))
        return [p.export_device for p in row.profiles] if row else []

    # ── Filter ──

    def set_filter(self, game: str = "", search: str = "") -> None:
        self._game_filter = game or ""
        self._search = (search or "").strip().casefold()
        self._apply_filter()

    def _apply_filter(self) -> None:
        for i in range(self.treeWidget.topLevelItemCount()):
            root = self.treeWidget.topLevelItem(i)
            name_match = bool(self._search) and self._search in root.text(0).casefold()
            any_visible = False
            for j in range(root.childCount()):
                child = root.child(j)
                entry: ProfileEntry = child.data(COLUMN_NAME, PROFILE_ROLE)
                visible = True
                if self._game_filter and entry.game != self._game_filter:
                    visible = False
                if (
                    visible
                    and self._search
                    and not name_match
                    and self._search not in entry.profile_name.casefold()
                ):
                    visible = False
                child.setHidden(not visible)
                any_visible = any_visible or visible
            root.setHidden(not any_visible and root.childCount() > 0)
            if (self._search or self._game_filter) and any_visible and not name_match:
                root.setExpanded(True)

    # ── Context menu ──

    def _show_context_menu(self, position) -> None:
        item = self.treeWidget.itemAt(position)
        if item is None:
            return
        row = self.model.row(item.data(COLUMN_NAME, ROW_KEY_ROLE))
        if row is None:
            return
        menu = QMenu(self)
        preview_action = layout_action = None
        if row.kind == KIND_CONTROLLER:
            entry = item.data(COLUMN_NAME, PROFILE_ROLE)
            target = entry.export_device if entry is not None else None
            if target is None and row.profiles:
                target = row.profiles[0].export_device
            preview_action = menu.addAction(S.MENU_PREVIEW)
            preview_action.setEnabled(target is not None)
            layout_action = menu.addAction(S.MENU_EDIT_LAYOUT)
        else:
            target = None
            layout_action = menu.addAction(S.PAGES_EDIT_LAYOUT)
        action = menu.exec(self.treeWidget.viewport().mapToGlobal(position))
        if action is None:
            return
        if action == preview_action and target is not None:
            self.preview_requested.emit(target)
        elif action == layout_action:
            if row.kind == KIND_CONTROLLER and row.guid:
                self.edit_layout_requested.emit(row.guid)
            elif row.page is not None:
                self.page_layout_requested.emit(row.page.page_id)


if __name__ == "__main__":
    pass
