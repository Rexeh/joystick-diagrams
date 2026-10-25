"""4. Diagrams › Layout: the hybrid layout editor screen (plan §5.5.5, §5.6, J11).

Header: the **Diagram** picker lists the controllers with a template, then the
controllers that still need one (greyed, "needs a template · Choose template…"
in place), then the combined pages ("▣ <page>"), and **Preview with** (which
profile's bindings are shown) and **Changes apply to** (which layer new changes
go to: all profiles on this diagram, or only the previewed profile). Toolbar:
select, add a modifier box, auto-add, add a note, hide, undo/redo, zoom and
the More menu. Canvas: a lazily created ``LayoutEditorView`` (QtWebEngine)
showing ``render_for_editor``'s SVG with an overlay for dragging. Right panel:
the selected box (name, origin, X/Y/W/H spin boxes as the keyboard
alternative to dragging), modifier-box actions, and plain-language notices.

Page mode (a page chosen in the picker): the canvas shows the page composed by
``render/compose.py`` on the thread pool (debounced, zoom kept between
renders) and the right panel is ``layout_page_panel.PagePanel``: name, the
controllers on the page, which profiles it is made for, arrangement, page size,
orientation, scale, gap, title and date. Each change is saved at once through
``PageService`` and is one undo step (``PageHistory``); Preview with lists only
the page's profiles. The box tools (modifier box, auto-add, note, hide) are
disabled, and a controller chosen in the panel offers "Edit this controller's
boxes ›". Free placement of panels and page notes come in v2.

Every gesture becomes layout ops persisted at once through
``LayoutEditSession`` → ``LayoutService`` (so they survive the page being
destroyed on reprocess and are picked up by the next export); the render runs
on the global ``QThreadPool`` with a generation counter so the UI thread never
blocks and stale results are dropped. ``refresh()`` is cheap: it only reloads
the device list and re-renders when something changed.

Layouts belong to a controller: the session is created with
``device_guid=export_device.device_id`` so every read and write is keyed by
(template, controller, profile).
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import qtawesome as qta
from PySide6.QtCore import (
    QObject,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QStackedLayout,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db import db_settings
from joystick_diagrams.modifier_identity import (
    ModifierDisplay,
    get_modifier_display,
    modifiers_in_main_text,
    set_modifier_display,
)
from joystick_diagrams.render import RenderContext, build_render_context
from joystick_diagrams.render.editor import (
    EditorOptions,
    EditorRender,
    render_for_editor,
)
from joystick_diagrams.render.layout import TEMPLATE_LAYER, LayoutLayers
from joystick_diagrams.render.layout_apply import LayoutSlotInfo
from joystick_diagrams.ui import strings_diagrams as D
from joystick_diagrams.ui import strings_layout as S
from joystick_diagrams.ui.layout_editor.bridge import EditorBridge
from joystick_diagrams.ui.layout_editor.panel_style import (
    LABEL_STYLE,
    MUTED_STYLE,
    NOTICE_STYLE,
    PROFILE_STYLE,
)
from joystick_diagrams.ui.layout_editor.panel_style import heading_label as _heading
from joystick_diagrams.ui.layout_editor.panel_style import help_label as _help
from joystick_diagrams.ui.layout_editor.panel_style import panel_button as _panel_button
from joystick_diagrams.ui.layout_editor.panel_style import tool_button as _tool
from joystick_diagrams.ui.layout_editor.planning import (
    SceneCache,
    box_count,
    next_box_index,
    plan_one_box,
)
from joystick_diagrams.ui.layout_editor.session import LayoutEditSession
from joystick_diagrams.ui.layout_page_panel import (
    PageHistory,
    PagePanel,
    default_update,
    same_page,
)
from joystick_diagrams.ui.widgets.confirm import confirm, show_list
from joystick_diagrams.ui.widgets.empty_state import EmptyState

_logger = logging.getLogger(__name__)

LAYOUT_EDITOR_LAST_DEVICE_SETTING_KEY = "layout_editor_last_device"
LAYOUT_EDITOR_LAST_PROFILE_SETTING_KEY = "layout_editor_last_profile"
LAYOUT_EDITOR_LAST_SCOPE_SETTING_KEY = "layout_editor_last_scope"
LAYOUT_EDITOR_ZOOM_SETTING_KEY = "layout_editor_zoom"
ENTRY_PREFIX_NEEDS = "needs:"
ENTRY_PREFIX_PAGE = "page:"
SCOPE_ALL = "all"
SCOPE_PROFILE = "profile"
RENDER_DEBOUNCE_MS = 40
PAGE_RENDER_DEBOUNCE_MS = 120
PAGE_ZOOM_STEP = 1.25
PANEL_WIDTH = 320
NOTE_WIDTH = 220.0
NOTE_HEIGHT = 26.0
NOTE_MARGIN = 20.0
DEFAULT_BOX_SCALE = 0.85


# ── Data ──


@dataclass
class DiagramEntry:
    """One device with a template, and every profile that uses it."""

    device_id: str
    device_name: str
    template: Any
    export_devices: list[Any]

    @property
    def template_key(self) -> str:
        return self.template.template_key

    def profile_entries(self) -> list[tuple[str, Any]]:
        return [
            (
                S.PREVIEW_ENTRY.format(
                    game=ed.profile_wrapper.profile_origin.name,
                    profile=ed.profile_wrapper.profile_name,
                ),
                ed,
            )
            for ed in self.export_devices
        ]


def load_export_devices() -> list[Any]:
    from joystick_diagrams.ui.device_setup_controller import get_export_devices

    try:
        return list(get_export_devices())
    except Exception as e:  # noqa: BLE001 - never let the screen fail to open
        _logger.warning(f"Could not load devices for the layout editor: {e}")
        return []


def controllers_needing_template() -> list[tuple[str, str]]:
    """``(guid, name)`` of controllers that get a diagram once they have a template."""
    try:
        from joystick_diagrams.device_status import DeviceStatus, all_device_statuses

        statuses = all_device_statuses(
            list(AppState().profile_wrappers), include_unseen=False
        )
    except Exception as e:  # noqa: BLE001
        _logger.warning(f"Could not work out controller statuses: {e}")
        return []
    waiting = (DeviceStatus.NEEDS_TEMPLATE, DeviceStatus.TEMPLATE_MISSING)
    found = [
        (guid, info.name or guid)
        for guid, info in statuses.items()
        if info.state in waiting
    ]
    return sorted(found, key=lambda item: item[1].casefold())


def load_pages() -> list[Any]:
    try:
        return list(AppState().page_service.pages())
    except Exception as e:  # noqa: BLE001
        _logger.warning(f"Could not load pages: {e}")
        return []


def load_diagrams(export_devices: list[Any] | None = None) -> list[DiagramEntry]:
    """Devices with a template, grouped from ``get_export_devices()``."""
    if export_devices is None:
        export_devices = load_export_devices()
    devices = [ed for ed in export_devices if ed.has_template]
    service = AppState().device_service
    grouped: dict[str, DiagramEntry] = {}
    for ed in devices:
        entry = grouped.get(ed.device_id)
        if entry is None:
            entry = DiagramEntry(
                ed.device_id,
                service.resolve_name(ed.device_id, ed.device_name),
                ed.template,
                [],
            )
            grouped[ed.device_id] = entry
        entry.export_devices.append(ed)
    return list(grouped.values())


@dataclass(frozen=True)
class Notice:
    text: str
    action_text: str | None = None
    action: Callable[[], None] | None = None


def command_label(export_device: Any, input_key: str) -> str:
    """The bound command for ``input_key`` (custom label applied), else the key."""
    try:
        inputs = export_device.device.get_combined_inputs()
        bound = inputs.get(input_key) or inputs.get(input_key.upper())
        command = getattr(bound, "command", "") if bound is not None else ""
        if command:
            if AppState._inst is not None:
                command = AppState().label_service.resolve(command)
            return command
    except Exception:  # noqa: BLE001 - labels are decoration only
        pass
    return S.pretty_key(input_key)


def file_date(path: Path | None) -> str:
    try:
        if path is not None:
            return datetime.fromtimestamp(path.stat().st_mtime).strftime("%d %b %Y")
    except OSError:
        pass
    return "an unknown date"


# ── Rendering off the UI thread ──


class _RenderSignals(QObject):
    done = Signal(int, object)
    failed = Signal(int, str)


class LayoutRenderRunnable(QRunnable):
    def __init__(
        self,
        generation: int,
        template: Any,
        export_device: Any,
        layers: LayoutLayers,
        ctx: RenderContext,
    ):
        super().__init__()
        self.generation = generation
        self.template = template
        self.export_device = export_device
        self.layers = layers
        self.ctx = ctx
        self.signals = _RenderSignals()

    @Slot()
    def run(self) -> None:
        try:
            render = render_for_editor(
                self.template,
                self.export_device,
                layers=self.layers,
                options=EditorOptions(ctx=self.ctx),
            )
        except Exception as e:  # noqa: BLE001 - reported to the screen
            _logger.error(f"Layout render failed: {e}", exc_info=True)
            self.signals.failed.emit(self.generation, str(e))
            return
        self.signals.done.emit(self.generation, render)


class _PageSignals(QObject):
    done = Signal(int, object)  # generation, ComposeResult
    failed = Signal(int, str)


class PageRenderRunnable(QRunnable):
    """Composes a page for one profile off the UI thread (the page preview)."""

    def __init__(self, generation: int, page: Any, wrapper: Any, devices: list[Any]):
        super().__init__()
        self.generation = generation
        self.page = page
        self.wrapper = wrapper
        self.devices = devices
        self.ctx = build_render_context()
        self.signals = _PageSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = compose_page_result(
                self.page, self.wrapper, self.devices, self.ctx
            )
        except Exception as e:  # noqa: BLE001 - reported to the screen
            _logger.warning(f"Page preview failed: {e}")
            self.signals.failed.emit(self.generation, str(e))
            return
        self.signals.done.emit(self.generation, result)


def compose_page_result(page: Any, wrapper: Any, devices: list[Any], ctx=None) -> Any:
    """``compose_page`` for one profile (the ``ComposeResult``: SVG, warnings and
    the smallest printed font size)."""
    from joystick_diagrams.render.compose import (
        compose_page,
        member_devices_for_profile,
    )

    members = member_devices_for_profile(page, wrapper, devices)
    return compose_page(page, wrapper, members, ctx)


# ── Note dialog ──


class NoteDialog(QDialog):
    """Note text with "Insert profile name" / "Insert date" helpers (no raw tokens)."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(S.NOTE_DIALOG_TITLE)
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        self.edit = QLineEdit(text)
        self.edit.setAccessibleName(S.NOTE_DIALOG_TITLE)
        layout.addWidget(self.edit)
        layout.addWidget(_help(S.NOTE_DIALOG_HELP))
        row = QHBoxLayout()
        self.insert_profile = QPushButton(S.NOTE_INSERT_PROFILE)
        self.insert_profile.setProperty("class", "plugin-setup-button")
        self.insert_profile.clicked.connect(lambda: self._insert(S.NOTE_PROFILE_TOKEN))
        self.insert_date = QPushButton(S.NOTE_INSERT_DATE)
        self.insert_date.setProperty("class", "plugin-setup-button")
        self.insert_date.clicked.connect(lambda: self._insert(S.NOTE_DATE_TOKEN))
        row.addWidget(self.insert_profile)
        row.addWidget(self.insert_date)
        row.addStretch(1)
        layout.addLayout(row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _insert(self, token: str) -> None:
        self.edit.insert(token)
        self.edit.setFocus()

    def text(self) -> str:
        return self.edit.text()


# ── The screen ──


class CustomiseLayout(QWidget):
    devices_changed = Signal()
    go_to_controllers_requested = Signal()
    pages_changed = Signal()  # a page was changed in page mode

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()
        self.service = self.appState.layout_service
        self._diagrams: list[DiagramEntry] = []
        self._needs_template: list[tuple[str, str]] = []
        self._pages: list[Any] = []
        self._all_devices: list[Any] = []
        self._page_profiles: list[Any] = []
        self._page_generation = 0
        self._page_view = None
        self.page_preview_svg: str | None = None
        self.page_compose_result: Any = None
        self._page_history: PageHistory | None = None
        self._page_zoom: float | None = None
        self._page_mode = False
        self._page_render_timer = QTimer(self)
        self._page_render_timer.setSingleShot(True)
        self._page_render_timer.setInterval(PAGE_RENDER_DEBOUNCE_MS)
        self._page_render_timer.timeout.connect(self._render_page)
        self._signature: list | None = None
        self._session: LayoutEditSession | None = None
        self._render: EditorRender | None = None
        self._export_device: Any = None
        self._selected: str | None = None
        self._pending_select: str | None = None
        self._generation = 0
        self._dirty = True
        self._loading = False
        self._canvas = None
        self._canvas_pending = False
        self._scenes = SceneCache()
        self._pool = QThreadPool.globalInstance()
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(RENDER_DEBOUNCE_MS)
        self._render_timer.timeout.connect(self._start_render)

        self.bridge = EditorBridge(self)
        self.bridge.gesture.connect(self._on_gesture)
        self.bridge.gesture_rejected.connect(self._set_status)
        self.bridge.selection_changed.connect(self._on_selection_changed)
        self.bridge.nudged.connect(self._on_nudge)
        self.bridge.undo_requested.connect(self.undo)
        self.bridge.redo_requested.connect(self.redo)
        self.bridge.hide_requested.connect(self._hide_target)
        self.bridge.note_edit_requested.connect(self._edit_note)
        self.bridge.zoom_changed.connect(self._on_zoom_changed)

        self._build_ui()
        self._page_shortcuts = []
        for keys, slot in (
            (QKeySequence.StandardKey.Undo, self.undo),
            (QKeySequence.StandardKey.Redo, self.redo),
            (QKeySequence("Ctrl+Y"), self.redo),
        ):
            shortcut = QShortcut(keys, self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(slot)
            shortcut.setEnabled(False)  # the canvas handles its own keys
            self._page_shortcuts.append(shortcut)

    # ── UI construction ──

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.help_label = _help(S.PAGE_HELP)
        self.help_label.setObjectName("device_help_label")
        root.addWidget(self.help_label)
        root.addLayout(self._build_header())

        self.banner = QWidget()
        self.banner.setProperty("class", "guidance-banner")
        banner_row = QHBoxLayout(self.banner)
        banner_row.setContentsMargins(12, 8, 12, 8)
        icon = QLabel()
        icon.setPixmap(
            qta.icon("fa5s.info-circle", color="#4C8BF5").pixmap(QSize(18, 18))
        )
        banner_row.addWidget(icon)
        self.banner_label = QLabel(S.UNSUPPORTED_BANNER)
        self.banner_label.setWordWrap(True)
        banner_row.addWidget(self.banner_label, 1)
        self.banner.hide()
        root.addWidget(self.banner)

        root.addLayout(self._build_toolbar())

        body = QHBoxLayout()
        body.setSpacing(12)
        self.canvas_stack_widget = QWidget()
        self.canvas_stack = QStackedLayout(self.canvas_stack_widget)
        self.canvas_stack.setContentsMargins(0, 0, 0, 0)
        self.empty_state = EmptyState(
            D.LAYOUT_NONE_READY, "fa5s.file-code", D.GO_TO_CONTROLLERS_NEXT
        )
        self.empty_state.action_requested.connect(self.go_to_controllers_requested.emit)
        self.needs_state = EmptyState("", "fa5s.file-code", D.CHOOSE_TEMPLATE)
        self.needs_state.action_requested.connect(self.choose_template_for_selected)
        self.page_host = QWidget()
        page_layout = QVBoxLayout(self.page_host)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(6)
        self.page_placeholder = QLabel(D.PAGE_PREVIEW_UPDATING)
        self.page_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_placeholder.setStyleSheet(
            "color: #9AA0A6; font-style: italic; background: #252830; "
            "border: 1px solid #3C4043; border-radius: 6px;"
        )
        page_layout.addWidget(self.page_placeholder, 1)
        self.canvas_host = QWidget()
        self.canvas_host.setMinimumSize(320, 240)
        host_layout = QVBoxLayout(self.canvas_host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas_placeholder = QLabel(S.RENDERING)
        self.canvas_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_placeholder.setStyleSheet(
            "color: #9AA0A6; font-style: italic; background: #252830; "
            "border: 1px solid #3C4043; border-radius: 6px;"
        )
        host_layout.addWidget(self.canvas_placeholder)
        self.canvas_stack.addWidget(self.empty_state)
        self.canvas_stack.addWidget(self.canvas_host)
        self.canvas_stack.addWidget(self.needs_state)
        self.canvas_stack.addWidget(self.page_host)
        body.addWidget(self.canvas_stack_widget, 1)
        self.panel_stack = QStackedWidget()
        self.panel_stack.setFixedWidth(PANEL_WIDTH)
        self.box_panel = self._build_panel()
        self.panel_stack.addWidget(self.box_panel)
        self.page_panel_scroll = self._build_page_panel()
        self.panel_stack.addWidget(self.page_panel_scroll)
        body.addWidget(self.panel_stack)
        root.addLayout(body, 1)

    def _build_header(self) -> QVBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(10)
        header.addWidget(_heading(S.HEADER_DIAGRAM))
        self.diagram_combo = QComboBox()
        self.diagram_combo.setProperty("class", "view-binds-list")
        self.diagram_combo.setMinimumWidth(320)  # "<controller> · <template>"
        self.diagram_combo.setAccessibleName(S.HEADER_DIAGRAM)
        self.diagram_combo.currentIndexChanged.connect(
            lambda _i: self._on_diagram_changed()
        )
        header.addWidget(self.diagram_combo)
        header.addSpacing(12)
        header.addWidget(_heading(S.HEADER_PREVIEW_WITH))
        self.profile_combo = QComboBox()
        self.profile_combo.setProperty("class", "view-binds-list")
        self.profile_combo.setMinimumWidth(200)
        self.profile_combo.setAccessibleName(S.HEADER_PREVIEW_WITH)
        self.profile_combo.currentIndexChanged.connect(
            lambda _i: self._on_profile_changed()
        )
        header.addWidget(self.profile_combo)
        header.addStretch(1)
        outer = QVBoxLayout()
        outer.setSpacing(8)
        outer.addLayout(header)
        header = QHBoxLayout()  # second row: Changes apply to · Saved automatically
        header.setSpacing(10)
        outer.addLayout(header)
        self.scope_heading = _heading(S.HEADER_SCOPE)
        header.addWidget(self.scope_heading)
        self.scope_group = QButtonGroup(self)
        self.scope_all = QRadioButton(S.SCOPE_ALL_PROFILES)
        self.scope_profile = QRadioButton(S.SCOPE_ONLY_PROFILE.format(profile="…"))
        self.scope_all.setChecked(True)
        self.scope_group.addButton(self.scope_all, 0)
        self.scope_group.addButton(self.scope_profile, 1)
        self.scope_group.idToggled.connect(self._on_scope_toggled)
        header.addWidget(self.scope_all)
        header.addWidget(self.scope_profile)
        header.addStretch(1)
        self.saved_label = QLabel(S.SAVED_AUTOMATICALLY)
        self.saved_label.setStyleSheet(MUTED_STYLE)
        saved_icon = QLabel()
        saved_icon.setPixmap(
            qta.icon("fa5s.check-circle", color="#34D399").pixmap(QSize(14, 14))
        )
        header.addWidget(saved_icon)
        header.addWidget(self.saved_label)
        return outer

    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.select_button = _tool(
            S.TOOL_SELECT, S.TOOLTIP_SELECT, "fa5s.mouse-pointer"
        )
        self.select_button.clicked.connect(lambda: self._select(None))
        self.add_box_button = _tool(S.TOOL_ADD_MODIFIER_BOX, S.TOOLTIP_ADD_MODIFIER_BOX)
        self.add_box_button.clicked.connect(self.add_modifier_box)
        self.auto_add_button = _tool(S.TOOL_AUTO_ADD, S.TOOLTIP_AUTO_ADD, "fa5s.magic")
        self.auto_add_button.clicked.connect(self.open_auto_add)
        self.add_note_button = _tool(S.TOOL_ADD_NOTE, "")
        self.add_note_button.clicked.connect(self.add_note)
        self.hide_button = _tool(S.TOOL_HIDE, S.TOOLTIP_HIDE, "fa5s.eye-slash")
        self.hide_button.clicked.connect(self.hide_selected)
        self.undo_button = _tool(S.TOOL_UNDO, S.TOOLTIP_UNDO, "fa5s.undo")
        self.undo_button.clicked.connect(self.undo)
        self.redo_button = _tool(S.TOOL_REDO, S.TOOLTIP_REDO, "fa5s.redo")
        self.redo_button.clicked.connect(self.redo)
        self.zoom_out_button = _tool("−", S.TOOL_ZOOM_OUT)
        self.zoom_out_button.setAccessibleName(S.TOOL_ZOOM_OUT)
        self.zoom_out_button.clicked.connect(lambda: self._zoom("out"))
        self.zoom_label = QPushButton("100%")
        self.zoom_label.setFlat(True)
        self.zoom_label.setStyleSheet(
            "QPushButton { color: #E8EAED; background: transparent; border: none; min-width: 44px; }"
        )
        self.zoom_label.setToolTip(S.TOOLTIP_ZOOM_100)
        self.zoom_label.clicked.connect(lambda: self._zoom("100"))
        self.zoom_in_button = _tool("+", S.TOOL_ZOOM_IN)
        self.zoom_in_button.setAccessibleName(S.TOOL_ZOOM_IN)
        self.zoom_in_button.clicked.connect(lambda: self._zoom("in"))
        self.fit_button = _tool(S.TOOL_ZOOM_FIT, S.TOOLTIP_ZOOM_FIT)
        self.fit_button.clicked.connect(lambda: self._zoom("fit"))
        self.more_button = _tool(S.TOOL_MORE + " ▾", S.TOOL_MORE)
        self.more_menu = QMenu(self)
        self.undo_profile_action = self.more_menu.addAction(
            S.MORE_UNDO_PROFILE.format(profile="…")
        )
        self.undo_profile_action.triggered.connect(self.undo_profile_changes)
        self.reset_all_action = self.more_menu.addAction(S.MORE_RESET_ALL)
        self.reset_all_action.triggered.connect(self.reset_all)
        self.more_menu.addSeparator()
        self.save_as_action = self.more_menu.addAction(S.MORE_SAVE_AS_TEMPLATE)
        self.save_as_action.triggered.connect(self.save_as_template)
        self.more_button.setMenu(self.more_menu)
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        for widget in (
            self.select_button,
            self.add_box_button,
            self.auto_add_button,
            self.add_note_button,
            self.hide_button,
        ):
            bar.addWidget(widget)
        bar.addWidget(self._separator())
        bar.addWidget(self.undo_button)
        bar.addWidget(self.redo_button)
        bar.addWidget(self._separator())
        bar.addWidget(self.zoom_out_button)
        bar.addWidget(self.zoom_label)
        bar.addWidget(self.zoom_in_button)
        bar.addWidget(self.fit_button)
        bar.addStretch(1)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(MUTED_STYLE)
        bar.addWidget(self.status_label)
        bar.addWidget(self.more_button)
        self.tool_buttons = [
            self.add_box_button,
            self.auto_add_button,
            self.add_note_button,
            self.hide_button,
            self.undo_button,
            self.redo_button,
            self.zoom_out_button,
            self.zoom_in_button,
            self.fit_button,
            self.more_button,
        ]
        # Box tools that don't apply to a page (page mode disables them)
        self.box_only_tools = [
            self.select_button,
            self.add_box_button,
            self.auto_add_button,
            self.add_note_button,
            self.hide_button,
        ]
        self._box_tool_tips = {id(b): b.toolTip() for b in self.box_only_tools}
        return bar

    @staticmethod
    def _separator() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #3C4043;")
        return line

    def _build_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(PANEL_WIDTH)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        panel = QWidget()
        panel.setProperty("class", "surface-card")
        panel.setMaximumWidth(PANEL_WIDTH - 4)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.panel_empty = _help(S.PANEL_NOTHING_SELECTED)
        layout.addWidget(self.panel_empty)

        self.panel_selection = QWidget()
        sel = QVBoxLayout(self.panel_selection)
        sel.setContentsMargins(0, 0, 0, 0)
        sel.setSpacing(6)
        self.selection_title = _heading("")
        sel.addWidget(self.selection_title)
        self.selection_origin = QLabel("")
        self.selection_origin.setStyleSheet(MUTED_STYLE)
        sel.addWidget(self.selection_origin)
        self.selection_profile = QLabel("")
        self.selection_profile.setStyleSheet(PROFILE_STYLE)
        self.selection_profile.hide()
        sel.addWidget(self.selection_profile)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        self.spin_x = self._spin(S.PANEL_X_NAME)
        self.spin_y = self._spin(S.PANEL_Y_NAME)
        self.spin_w = self._spin(S.PANEL_W_NAME)
        self.spin_h = self._spin(S.PANEL_H_NAME)
        for column, (text, spin) in enumerate(
            (
                (S.PANEL_X, self.spin_x),
                (S.PANEL_Y, self.spin_y),
                (S.PANEL_W, self.spin_w),
                (S.PANEL_H, self.spin_h),
            )
        ):
            label = QLabel(text)
            label.setStyleSheet(LABEL_STYLE)
            grid.addWidget(label, 0, column)
            grid.addWidget(spin, 1, column)
        sel.addLayout(grid)
        self.spin_x.editingFinished.connect(self._on_position_edited)
        self.spin_y.editingFinished.connect(self._on_position_edited)
        self.spin_w.editingFinished.connect(self._on_size_edited)
        self.spin_h.editingFinished.connect(self._on_size_edited)
        self.capability_hint = _help("")
        self.capability_hint.hide()
        sel.addWidget(self.capability_hint)

        self.modifier_count_label = QLabel("")
        self.modifier_count_label.setStyleSheet(LABEL_STYLE)
        self.modifier_count_label.setWordWrap(True)
        sel.addWidget(self.modifier_count_label)
        self.panel_add_box = _panel_button(S.PANEL_ADD_BOX)
        self.panel_add_box.clicked.connect(self.add_modifier_box)
        sel.addWidget(self.panel_add_box)
        self.panel_hide = _panel_button(S.PANEL_HIDE_BOX)
        self.panel_hide.clicked.connect(self.hide_selected)
        sel.addWidget(self.panel_hide)
        self.panel_edit_note = _panel_button(S.PANEL_EDIT_NOTE)
        self.panel_edit_note.clicked.connect(
            lambda: self._edit_note(self._selected or "")
        )
        sel.addWidget(self.panel_edit_note)
        self.panel_undo_box = _panel_button(S.PANEL_UNDO_BOX)
        self.panel_undo_box.clicked.connect(self.undo_changes_to_selected)
        sel.addWidget(self.panel_undo_box)
        self.panel_selection.hide()
        layout.addWidget(self.panel_selection)

        layout.addSpacing(8)
        layout.addWidget(_heading(S.PANEL_NOTICES))
        self.notices_box = QVBoxLayout()
        self.notices_box.setSpacing(6)
        layout.addLayout(self.notices_box)
        self.no_notices = _help(S.PANEL_NO_NOTICES)
        layout.addWidget(self.no_notices)
        layout.addStretch(1)
        self.undo_note = _help(S.PANEL_UNDO_NOTE)
        layout.addWidget(self.undo_note)
        scroll.setWidget(panel)
        return scroll

    def _build_page_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(PANEL_WIDTH)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        card = QWidget()
        card.setProperty("class", "surface-card")
        card.setMaximumWidth(PANEL_WIDTH - 4)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        self.page_panel = PagePanel(card)
        self.page_panel.edited.connect(self._on_page_edited)
        self.page_panel.change_controllers_requested.connect(
            self.change_page_controllers
        )
        self.page_panel.edit_controller_requested.connect(self.show_device)
        self.page_panel.reset_requested.connect(self.reset_page)
        layout.addWidget(self.page_panel)
        scroll.setWidget(card)
        return scroll

    @staticmethod
    def _spin(name: str) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(-20000, 20000)
        spin.setAccessibleName(name)
        spin.setKeyboardTracking(False)
        spin.setProperty("class", "view-binds-list")
        spin.setMinimumWidth(0)
        spin.setMaximumWidth(68)
        spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        return spin

    # ── Lifecycle ──

    def refresh(self) -> None:
        """Cheap: reload the device list; re-render only when something changed."""
        self._reload_diagrams()
        if self._dirty and self.isVisible():
            self._render_timer.start()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        if self.current_page() is not None and self.page_preview_svg:
            self._show_page_svg(self.page_preview_svg)
            return
        if self._dirty:
            self._render_timer.start()
        elif self._canvas_pending and self._render is not None:
            self._push_to_canvas(self._render)

    def shutdown(self) -> None:
        self._render_timer.stop()
        self._page_render_timer.stop()
        self._generation += 1
        self._page_generation += 1
        if self._page_view is not None:
            self._page_view.shutdown()
            self._page_view.setParent(None)
            self._page_view = None
        if self._canvas is not None:
            self._canvas.shutdown()
            self._canvas.setParent(None)
            self._canvas = None

    def closeEvent(self, event):  # noqa: N802
        self.shutdown()
        super().closeEvent(event)

    # ── Diagrams, profiles and scope ──

    def _reload_diagrams(self) -> None:
        devices = load_export_devices()
        diagrams = load_diagrams(devices)
        needs = controllers_needing_template()
        pages = load_pages()
        signature = [
            [
                (
                    d.device_id,
                    d.template_key,
                    [ed.profile_wrapper.profile_key for ed in d.export_devices],
                )
                for d in diagrams
            ],
            needs,
            [(p.page_id, p.name, p.updated_at) for p in pages],
        ]
        self._all_devices = devices
        if signature == self._signature:
            return
        self._signature = signature
        self._diagrams = diagrams
        self._needs_template = needs
        self._pages = pages
        current = self.diagram_combo.currentData()
        self._loading = True
        try:
            self.diagram_combo.clear()
            for entry in diagrams:
                self.diagram_combo.addItem(
                    S.DIAGRAM_ENTRY.format(
                        controller=entry.device_name,
                        template=Path(entry.template.template_file_name).stem,
                    ),
                    entry.device_id,
                )
            model = self.diagram_combo.model()
            for guid, name in needs:
                self.diagram_combo.addItem(
                    D.LAYOUT_PICKER_NEEDS_TEMPLATE.format(controller=name)
                    + f" · {D.CHOOSE_TEMPLATE}",
                    ENTRY_PREFIX_NEEDS + guid,
                )
                item = model.item(self.diagram_combo.count() - 1)
                if item is not None:
                    item.setForeground(Qt.GlobalColor.gray)
            for page in pages:
                self.diagram_combo.addItem(
                    D.LAYOUT_PICKER_PAGE.format(page=page.name),
                    ENTRY_PREFIX_PAGE + page.page_id,
                )
            wanted = current or db_settings.get_setting(
                LAYOUT_EDITOR_LAST_DEVICE_SETTING_KEY
            )
            index = self.diagram_combo.findData(wanted) if wanted else -1
            self.diagram_combo.setCurrentIndex(max(index, 0))
        finally:
            self._loading = False
        has_entries = self.diagram_combo.count() > 0
        if not has_entries:
            self.canvas_stack.setCurrentWidget(self.empty_state)
        for widget in self.tool_buttons:
            widget.setEnabled(bool(diagrams))
        self._on_diagram_changed()

    def current_entry_data(self) -> str | None:
        data = self.diagram_combo.currentData()
        return data if isinstance(data, str) else None

    def current_diagram(self) -> DiagramEntry | None:
        data = self.current_entry_data()
        if not data:
            return None
        return next((d for d in self._diagrams if d.device_id == data), None)

    def current_page(self) -> Any:
        data = self.current_entry_data() or ""
        if not data.startswith(ENTRY_PREFIX_PAGE):
            return None
        page_id = data[len(ENTRY_PREFIX_PAGE) :]
        return next((p for p in self._pages if p.page_id == page_id), None)

    def current_needs_template(self) -> tuple[str, str] | None:
        data = self.current_entry_data() or ""
        if not data.startswith(ENTRY_PREFIX_NEEDS):
            return None
        guid = data[len(ENTRY_PREFIX_NEEDS) :]
        return next((n for n in self._needs_template if n[0] == guid), None)

    def _set_editing_enabled(self, enabled: bool) -> None:
        for widget in self.tool_buttons:
            widget.setEnabled(enabled)
        for widget in (self.scope_all, self.scope_profile):
            widget.setEnabled(enabled)

    def _on_diagram_changed(self) -> None:
        if self._loading:
            return
        entry = self.current_diagram()
        self._selected = None
        self._render = None
        if entry is None:
            self._session = None
            self._export_device = None
            self._loading = True
            try:
                self.profile_combo.clear()
            finally:
                self._loading = False
            self._show_non_diagram()
            self._update_panel()
            return
        self.canvas_stack.setCurrentWidget(self.canvas_host)
        self._set_page_mode(False)
        self._set_editing_enabled(True)
        db_settings.add_update_setting_value(
            LAYOUT_EDITOR_LAST_DEVICE_SETTING_KEY, entry.device_id
        )
        self._loading = True
        try:
            self.profile_combo.clear()
            for text, ed in entry.profile_entries():
                self.profile_combo.addItem(text, ed.profile_wrapper.profile_key)
            wanted = db_settings.get_setting(LAYOUT_EDITOR_LAST_PROFILE_SETTING_KEY)
            index = self.profile_combo.findData(wanted) if wanted else -1
            self.profile_combo.setCurrentIndex(max(index, 0))
        finally:
            self._loading = False
        content_hash = None
        try:
            content_hash = entry.template.content_hash
        except OSError:
            pass
        self._session = LayoutEditSession(
            self.service,
            entry.template_key,
            content_hash,
            device_guid=entry.device_id,
        )
        self._on_profile_changed()

    def _show_non_diagram(self) -> None:
        """A greyed controller (needs a template) or a page (the Page panel)."""
        self._set_editing_enabled(False)
        needs = self.current_needs_template()
        page = self.current_page()
        if page is None:
            self._set_page_mode(False)
        if needs is not None:
            self.needs_state.set_message(
                D.LAYOUT_NEEDS_TEMPLATE_EMPTY.format(controller=needs[1])
            )
            self.canvas_stack.setCurrentWidget(self.needs_state)
        elif page is not None:
            self._show_page(page)
        else:
            self.canvas_stack.setCurrentWidget(self.empty_state)

    def choose_template_for_selected(self) -> None:
        needs = self.current_needs_template()
        if needs is None:
            return
        from joystick_diagrams.ui.export_page import choose_template_for

        guid, name = needs
        if choose_template_for(self, guid, name):
            self._signature = None
            self.devices_changed.emit()
            self.refresh()
            self.show_device(guid)

    # ── Pages (the Page panel) ──

    @property
    def page_service(self):
        return self.appState.page_service

    @property
    def page_history(self) -> PageHistory | None:
        return self._page_history

    def _set_page_mode(self, on: bool) -> None:
        """Page mode: the Page panel, page undo and zoom; box tools are disabled."""
        self._page_mode = on
        self.panel_stack.setCurrentWidget(
            self.page_panel_scroll if on else self.box_panel
        )
        self.help_label.setText(D.LAYOUT_PAGE_PREVIEW_HELP if on else S.PAGE_HELP)
        for button in self.box_only_tools:
            button.setToolTip(
                S.PAGE_TOOL_UNAVAILABLE if on else self._box_tool_tips[id(button)]
            )
            if on:
                button.setEnabled(False)
        self.more_button.setVisible(not on)
        for widget in (self.scope_heading, self.scope_all, self.scope_profile):
            widget.setVisible(not on)
        for shortcut in self._page_shortcuts:
            shortcut.setEnabled(on)
        if on:
            for button in (
                self.zoom_out_button,
                self.zoom_in_button,
                self.fit_button,
            ):
                button.setEnabled(True)
            self._update_history_buttons()

    def _show_page(self, page: Any) -> None:
        self.canvas_stack.setCurrentWidget(self.page_host)
        if self._page_history is None or self._page_history.page_id != page.page_id:
            self._page_history = PageHistory(page.page_id)
            self._page_zoom = None
            self.page_panel.select_controller(None)
            self.page_panel.set_problem("")
        self._set_page_mode(True)
        self._reload_page_profiles(page)
        self._load_page_panel(page)
        self._render_page()

    def _reload_page_profiles(self, page: Any) -> None:
        """The Preview with list: only the profiles this page is made for."""
        from joystick_diagrams.export import page_profiles

        try:
            self._page_profiles = page_profiles(page, self._all_devices)
        except Exception as e:  # noqa: BLE001
            _logger.warning(f"Could not list the profiles for {page.name}: {e}")
            self._page_profiles = []
        current = self.profile_combo.currentData()
        self._loading = True
        try:
            self.profile_combo.clear()
            for wrapper in self._page_profiles:
                self.profile_combo.addItem(
                    S.PREVIEW_ENTRY.format(
                        game=wrapper.profile_origin.name,
                        profile=wrapper.profile_name,
                    ),
                    wrapper.profile_key,
                )
            index = self.profile_combo.findData(current) if current else -1
            self.profile_combo.setCurrentIndex(max(index, 0))
        finally:
            self._loading = False

    def _page_rule_counts(self, page: Any) -> dict:
        from joystick_diagrams.render.compose import page_profile_plan
        from joystick_diagrams.render.page import ProfileRule

        counts = {}
        for rule in ProfileRule:
            try:
                counts[rule] = len(page_profile_plan(page, self._all_devices, rule))
            except Exception as e:  # noqa: BLE001
                _logger.debug(f"No profile plan for {page.name}: {e}")
                counts[rule] = 0
        return counts

    def _controller_names(self) -> dict[str, str]:
        service = self.appState.device_service
        names: dict[str, str] = {}
        for ed in self._all_devices:
            if ed.device_id not in names:
                names[ed.device_id] = service.resolve_name(ed.device_id, ed.device_name)
        return names

    def _load_page_panel(self, page: Any) -> None:
        wrapper = self._current_page_wrapper()
        self.page_panel.load(
            page,
            self._controller_names(),
            self._page_rule_counts(page),
            wrapper.profile_name if wrapper is not None else "",
        )
        if self.page_compose_result is not None:
            self.page_panel.set_compose_result(self.page_compose_result)

    def _current_page_wrapper(self) -> Any:
        index = self.profile_combo.currentIndex()
        if 0 <= index < len(self._page_profiles):
            return self._page_profiles[index]
        return None

    # Edits: every change saves at once through PageService (one undo step)

    def _on_page_edited(self, update: dict) -> None:
        page = self.current_page()
        if page is None:
            return
        from joystick_diagrams.render.page import Arrangement

        if "arrangement" in update and set(update) == {"arrangement"}:
            candidate = page.model_copy(
                update={
                    "arrangement": Arrangement(update["arrangement"]),
                    "placements": [
                        p.model_copy(update={"x_mm": None, "y_mm": None})
                        for p in page.placements
                    ],
                }
            )
            if same_page(candidate, page):
                return
            self._save_page(
                page,
                lambda: self.page_service.arrange(
                    page.page_id, Arrangement(update["arrangement"])
                ),
            )
            return
        try:
            candidate = type(page).model_validate({**page.model_dump(), **update})
        except ValueError as error:
            _logger.warning(f"Page change not applied to {page.name}: {error}")
            self._load_page_panel(page)
            return
        if same_page(candidate, page):
            return
        self._save_page(page, lambda: self.page_service.save(candidate))

    def reset_page(self) -> None:
        """Reset to defaults: page size, arrangement, scale, gap, title and date."""
        page = self.current_page()
        if page is None:
            return
        candidate = page.model_copy(update=default_update(page))
        if same_page(candidate, page):
            return
        self._save_page(page, lambda: self.page_service.save(candidate))

    def _save_page(self, before: Any, save: Callable[[], Any], record=True) -> Any:
        try:
            saved = save()
        except ValueError as error:
            self.page_panel.set_problem(str(error))
            self._load_page_panel(before)
            return None
        self.page_panel.set_problem("")
        if record and self._page_history is not None:
            self._page_history.record(before, saved)
        self._page_saved(before, saved)
        return saved

    def _page_saved(self, before: Any, saved: Any) -> None:
        """Keep the picker, Preview with, the panel and the preview in step."""
        self._pages = [saved if p.page_id == saved.page_id else p for p in self._pages]
        index = self.diagram_combo.findData(ENTRY_PREFIX_PAGE + saved.page_id)
        if index >= 0:
            self.diagram_combo.setItemText(
                index, D.LAYOUT_PICKER_PAGE.format(page=saved.name)
            )
        if self._signature is not None:
            self._signature[2] = [
                (p.page_id, p.name, p.updated_at) for p in self._pages
            ]
        if (
            before.profile_rule != saved.profile_rule
            or before.member_guids != saved.member_guids
        ):
            self._reload_page_profiles(saved)
        self._load_page_panel(saved)
        self._update_history_buttons()
        self._page_render_timer.start()
        self.pages_changed.emit()

    def undo_page_change(self) -> None:
        self._step_page_history(undo=True)

    def redo_page_change(self) -> None:
        self._step_page_history(undo=False)

    def _step_page_history(self, undo: bool) -> None:
        page = self.current_page()
        history = self._page_history
        if page is None or history is None:
            return
        target = history.undo() if undo else history.redo()
        if target is None:
            return
        restored = target.model_copy(update={"updated_at": page.updated_at})
        self._save_page(page, lambda: self.page_service.save(restored), record=False)

    def change_page_controllers(self) -> None:
        """Change controllers…: the Combine dialog for this page (one undo step)."""
        page = self.current_page()
        if page is None:
            return
        saved = self.open_page_dialog(page)
        if saved is None or same_page(saved, page):
            return
        if self._page_history is not None:
            self._page_history.record(page, saved)
        self._page_saved(page, saved)

    def open_page_dialog(self, page: Any) -> Any:
        from joystick_diagrams.ui.pages_dialog import PagesDialog

        dialog = PagesDialog(self, page, export_devices=list(self._all_devices))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.page

    # Rendering: compose_page on the thread pool; stale results are dropped

    def _render_page(self, synchronous: bool = False) -> Any:
        self._page_render_timer.stop()
        page = self.current_page()
        wrapper = self._current_page_wrapper()
        self._page_generation += 1
        if page is None or wrapper is None:
            self.page_placeholder.setText(D.PAGE_PREVIEW_UNAVAILABLE)
            return None
        self.page_placeholder.setText(D.PAGE_PREVIEW_UPDATING)
        self._set_status(S.RENDERING)
        if synchronous:
            try:
                result = compose_page_result(
                    page, wrapper, self._all_devices, build_render_context()
                )
            except Exception as e:  # noqa: BLE001
                self._on_page_failed(self._page_generation, str(e))
                return None
            self._on_page_rendered(self._page_generation, result)
            return result
        runnable = PageRenderRunnable(
            self._page_generation, page, wrapper, list(self._all_devices)
        )
        runnable.signals.done.connect(self._on_page_rendered)
        runnable.signals.failed.connect(self._on_page_failed)
        self._pool.start(runnable)
        return None

    def render_page_synchronously(self) -> str | None:
        result = self._render_page(synchronous=True)
        return result.svg_text if result is not None else None

    def _on_page_rendered(self, generation: int, result: Any) -> None:
        if generation != self._page_generation:
            return
        self.page_compose_result = result
        self.page_preview_svg = result.svg_text
        self._set_status("")
        self.page_panel.set_compose_result(result)
        if self.isVisible():
            self._show_page_svg(result.svg_text)

    def _show_page_svg(self, svg: str) -> None:
        view = self._ensure_page_view()
        if view is not None:
            view.show_svg(svg)

    def _on_page_failed(self, generation: int, message: str) -> None:
        if generation != self._page_generation:
            return
        self._set_status("")
        self.page_placeholder.setText(S.RENDER_FAILED)

    def _ensure_page_view(self):
        if self._page_view is not None:
            return self._page_view
        try:
            from joystick_diagrams.ui.layout_editor.view import SvgDocumentView
        except ImportError as e:  # pragma: no cover - WebEngine is a hard dependency
            _logger.error(f"QtWebEngine unavailable for the page preview: {e}")
            return None
        self._page_view = SvgDocumentView(self.page_host)
        self._page_view.loadFinished.connect(self._on_page_view_loaded)
        layout = self.page_host.layout()
        layout.removeWidget(self.page_placeholder)
        self.page_placeholder.hide()
        layout.addWidget(self._page_view, 1)
        return self._page_view

    def _on_page_view_loaded(self, _ok: bool) -> None:
        """Fit the first time a page is shown; afterwards keep the player's zoom."""
        view = self._page_view
        if view is None:
            return
        if self._page_zoom is None:
            self._page_zoom = view.fit_page()
        else:
            view.set_zoom(self._page_zoom)
        if self._page_zoom:
            self.zoom_label.setText(f"{round(self._page_zoom * 100)}%")

    def _zoom(self, mode: str) -> None:
        if not self._page_mode:
            self.bridge.request_zoom(mode)
            return
        view = self._page_view
        if view is None:
            return
        current = view.zoom()
        if mode == "in":
            factor = current * PAGE_ZOOM_STEP
        elif mode == "out":
            factor = current / PAGE_ZOOM_STEP
        elif mode == "100":
            factor = 1.0
        else:
            factor = view.fit_page() or current
        factor = max(0.1, min(5.0, factor))
        view.set_zoom(factor)
        self._page_zoom = factor
        self.zoom_label.setText(f"{round(factor * 100)}%")

    def show_page(self, page_id: str) -> None:
        """Select a page in the Diagram picker (Pages › Edit in Layout ›)."""
        self._reload_diagrams()
        index = self.diagram_combo.findData(ENTRY_PREFIX_PAGE + page_id)
        if index >= 0 and index != self.diagram_combo.currentIndex():
            self.diagram_combo.setCurrentIndex(index)

    def _on_profile_changed(self) -> None:
        if self._loading:
            return
        page = self.current_page()
        if page is not None:
            wrapper = self._current_page_wrapper()
            self.page_panel.set_profile_name(
                wrapper.profile_name if wrapper is not None else ""
            )
            self._render_page()
            return
        entry = self.current_diagram()
        index = self.profile_combo.currentIndex()
        if entry is None or not (0 <= index < len(entry.export_devices)):
            self._export_device = None
            return
        self._export_device = entry.export_devices[index]
        profile_key = self._export_device.profile_wrapper.profile_key
        db_settings.add_update_setting_value(
            LAYOUT_EDITOR_LAST_PROFILE_SETTING_KEY, profile_key
        )
        if self._session is not None:
            self._session.set_profile(profile_key)
        name = self._export_device.profile_wrapper.profile_name
        self.scope_profile.setText(S.SCOPE_ONLY_PROFILE.format(profile=name))
        self.undo_profile_action.setText(S.MORE_UNDO_PROFILE.format(profile=name))
        self._loading = True
        try:
            scope = (
                db_settings.get_setting(LAYOUT_EDITOR_LAST_SCOPE_SETTING_KEY)
                or SCOPE_ALL
            )
            (
                self.scope_profile if scope == SCOPE_PROFILE else self.scope_all
            ).setChecked(True)
        finally:
            self._loading = False
        self._apply_scope()
        self._invalidate()

    def _on_scope_toggled(self, button_id: int, checked: bool) -> None:
        if not checked or self._loading:
            return
        db_settings.add_update_setting_value(
            LAYOUT_EDITOR_LAST_SCOPE_SETTING_KEY,
            SCOPE_PROFILE if button_id == 1 else SCOPE_ALL,
        )
        self._apply_scope()

    def _apply_scope(self) -> None:
        if self._session is None:
            return
        if self.scope_profile.isChecked() and self._export_device is not None:
            self._session.set_scope(self._export_device.profile_wrapper.profile_key)
        else:
            self._session.set_scope(TEMPLATE_LAYER)

    @property
    def scope_layer(self) -> str:
        return self._session.scope if self._session is not None else TEMPLATE_LAYER

    @property
    def profile_name(self) -> str:
        if self._export_device is None:
            return ""
        return self._export_device.profile_wrapper.profile_name

    # ── Rendering ──

    def _invalidate(self) -> None:
        self._dirty = True
        if self.isVisible():
            self._render_timer.start()

    def _start_render(self) -> None:
        entry = self.current_diagram()
        if entry is None or self._session is None:
            self._dirty = False
            return
        self._dirty = False
        self._generation += 1
        self._set_status(S.RENDERING)
        runnable = LayoutRenderRunnable(
            self._generation,
            entry.template,
            self._export_device,
            self._session.layers(),
            build_render_context(),
        )
        runnable.signals.done.connect(self._on_rendered)
        runnable.signals.failed.connect(self._on_render_failed)
        self._pool.start(runnable)

    def render_synchronously(self) -> EditorRender | None:
        """Render on the calling thread (tests, scripts); same handling as the worker."""
        entry = self.current_diagram()
        if entry is None or self._session is None:
            return None
        self._dirty = False
        self._generation += 1
        render = render_for_editor(
            entry.template,
            self._export_device,
            layers=self._session.layers(),
            options=EditorOptions(ctx=build_render_context()),
        )
        self._on_rendered(self._generation, render)
        return render

    def _on_rendered(self, generation: int, render: EditorRender) -> None:
        if generation != self._generation:
            return
        self._render = render
        if self._pending_select is not None:
            self._selected = self._pending_select
            self._pending_select = None
        if self._selected is not None and self._slot_info(self._selected) is None:
            self._selected = None
        self._set_status("")
        self.banner.setVisible(not render.supported)
        self._push_to_canvas(render)
        self._update_panel()
        self._update_notices()
        self._update_history_buttons()

    def _on_render_failed(self, generation: int, message: str) -> None:
        if generation != self._generation:
            return
        self._set_status(S.RENDER_FAILED)

    def _push_to_canvas(self, render: EditorRender) -> None:
        if self._canvas is None and not self.isVisible():
            self._canvas_pending = True  # WebEngine starts the first time we're shown
            return
        self._canvas_pending = False
        canvas = self._ensure_canvas()
        if canvas is None:
            return
        payload = render.as_dict()
        payload["selected"] = self._selected or ""
        payload["profileLabel"] = self.profile_name
        canvas.show_document(render.svg_text, payload)

    def _ensure_canvas(self):
        if self._canvas is not None:
            return self._canvas
        try:
            from joystick_diagrams.ui.layout_editor.view import LayoutEditorView
        except ImportError as e:  # pragma: no cover - WebEngine is a hard dependency
            _logger.error(f"QtWebEngine unavailable for the layout editor: {e}")
            self.canvas_placeholder.setText(S.WEBENGINE_UNAVAILABLE)
            return None
        self._canvas = LayoutEditorView(self.canvas_host, bridge=self.bridge)
        layout = self.canvas_host.layout()
        layout.removeWidget(self.canvas_placeholder)
        self.canvas_placeholder.hide()
        layout.addWidget(self._canvas)
        return self._canvas

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    # ── Selection and panel ──

    def _slot_info(self, target: str | None) -> LayoutSlotInfo | None:
        if self._render is None or not target:
            return None
        for slot in self._render.slots:
            if slot.target == target:
                return slot
        return None

    def _on_selection_changed(self, target: str) -> None:
        self._selected = target or None
        self._update_panel()

    def _select(self, target: str | None) -> None:
        self._selected = target
        self.bridge.request_select(target)
        self._update_panel()

    def _on_zoom_changed(self, percent: int) -> None:
        if not self._page_mode:
            self.zoom_label.setText(f"{percent}%")

    def _update_panel(self) -> None:
        info = self._slot_info(self._selected)
        self.panel_empty.setVisible(info is None)
        self.panel_selection.setVisible(info is not None)
        if info is None:
            return
        is_note = info.role == "note"
        is_added = bool(info.added_uid)
        name = S.pretty_key(info.key) if not is_note else (info.text or S.PANEL_NOTE)
        origin = (
            S.PANEL_NOTE
            if is_note
            else (S.PANEL_ADDED_BY_YOU if is_added else S.PANEL_FROM_TEMPLATE)
        )
        self.selection_title.setText(name)
        self.selection_origin.setText(
            S.PANEL_ORIGIN.format(
                name=S.pretty_key(info.key) if not is_note else S.PANEL_NOTE,
                origin=origin,
            )
        )
        self.selection_profile.setVisible(info.layer == "profile")
        self.selection_profile.setText(
            S.PANEL_PROFILE_ONLY.format(profile=self.profile_name)
        )
        bbox = info.bbox
        for spin in (self.spin_x, self.spin_y, self.spin_w, self.spin_h):
            spin.blockSignals(True)
        if bbox is not None:
            self.spin_x.setValue(round(bbox.x))
            self.spin_y.setValue(round(bbox.y))
            self.spin_w.setValue(round(bbox.width))
            self.spin_h.setValue(round(bbox.height))
        for spin in (self.spin_x, self.spin_y, self.spin_w, self.spin_h):
            spin.blockSignals(False)
        self.spin_x.setEnabled(info.movable)
        self.spin_y.setEnabled(info.movable)
        self.spin_w.setEnabled(info.resizable)
        self.spin_h.setEnabled(info.resizable)
        hint = ""
        if not info.movable:
            hint = S.PANEL_NOT_MOVABLE
        elif not info.resizable:
            hint = S.PANEL_NOT_RESIZABLE
        self.capability_hint.setText(hint)
        self.capability_hint.setVisible(bool(hint))
        input_key = info.input_key
        show_boxes = bool(input_key) and info.role in (
            "action",
            "modifier",
            "modifier_key",
            "modifier_action",
        )
        self.modifier_count_label.setVisible(show_boxes)
        self.panel_add_box.setVisible(
            show_boxes and self._render is not None and self._render.supported
        )
        if show_boxes and self._render is not None:
            self.modifier_count_label.setText(
                S.PANEL_MODIFIER_BOXES.format(count=box_count(self._render, input_key))
            )
        if is_added:
            self.panel_hide.setText(
                S.PANEL_REMOVE_NOTE if is_note else S.PANEL_REMOVE_BOX
            )
        else:
            self.panel_hide.setText(
                S.PANEL_SHOW_BOX if info.hidden else S.PANEL_HIDE_BOX
            )
        self.panel_hide.setEnabled(self._render is not None and self._render.supported)
        self.panel_edit_note.setVisible(is_note)
        self.panel_undo_box.setVisible(not is_added and info.layer is not None)
        self.hide_button.setText(
            S.TOOL_REMOVE if is_added else (S.TOOL_SHOW if info.hidden else S.TOOL_HIDE)
        )

    def _update_history_buttons(self) -> None:
        if self._page_mode:
            history = self._page_history
            self.undo_button.setEnabled(history is not None and history.can_undo)
            self.redo_button.setEnabled(history is not None and history.can_redo)
            return
        session = self._session
        self.undo_button.setEnabled(session is not None and session.can_undo)
        self.redo_button.setEnabled(session is not None and session.can_redo)

    # ── Notices ──

    def _clear_notices(self) -> None:
        while self.notices_box.count():
            item = self.notices_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def build_notices(self) -> list[Notice]:
        render = self._render
        if render is None:
            return []
        notices: list[Notice] = []
        if not render.supported:
            notices.append(Notice(S.NOTICE_UNSUPPORTED))
        listed = modifiers_in_main_text(get_modifier_display())
        for key, count in sorted(render.overflow.items()):
            name = (
                command_label(self._export_device, key.lower())
                if self._export_device
                else S.pretty_key(key)
            )
            notices.append(
                Notice(
                    S.NOTICE_OVERFLOW.format(
                        name=name,
                        count=count,
                        s=S.plural(count),
                        tail=(
                            S.NOTICE_OVERFLOW_LISTED
                            if listed
                            else S.NOTICE_OVERFLOW_HIDDEN
                        ).format(
                            they=S.plural(count, "It", "They"),
                            dont=S.plural(count, "doesn't", "don't"),
                        ),
                    ),
                    S.NOTICE_OVERFLOW_ACTION if render.supported else None,
                    self.open_auto_add if render.supported else None,
                )
            )
        skipped = list(render.skipped_ops)
        if any(n.code == "template_updated" for n in render.notices):
            entry = self.current_diagram()
            path = entry.template.template_path if entry is not None else None
            count = len(skipped)
            notices.append(
                Notice(
                    S.NOTICE_TEMPLATE_UPDATED.format(
                        date=file_date(path),
                        count=count,
                        was=S.plural(count, "was", "were"),
                    ),
                    S.NOTICE_TEMPLATE_UPDATED_ACTION if skipped else None,
                    self.show_skipped if skipped else None,
                )
            )
        for notice in render.notices:
            name = S.pretty_key(notice.target or "")
            if notice.code == "box_unplaced":
                count = _leading_int(notice.detail)
                notices.append(
                    Notice(
                        S.NOTICE_NO_ROOM.format(
                            count=count, es=S.plural(count, "", "es"), name=name
                        )
                    )
                )
            elif notice.code == "resize_refused":
                notices.append(Notice(S.NOTICE_CANT_RESIZE.format(name=name)))
            elif notice.code in ("slot_missing", "parent_missing") and not any(
                n.code == "template_updated" for n in render.notices
            ):
                notices.append(Notice(S.NOTICE_MISSING_SLOT.format(name=name)))
        return notices

    def _update_notices(self) -> None:
        self._clear_notices()
        notices = self.build_notices()
        self.no_notices.setVisible(not notices)
        for notice in notices:
            frame = QFrame()
            frame.setObjectName("notice_frame")
            frame.setStyleSheet(NOTICE_STYLE)
            row = QVBoxLayout(frame)
            row.setContentsMargins(8, 6, 8, 6)
            row.setSpacing(4)
            label = QLabel(notice.text)
            label.setWordWrap(True)
            label.setStyleSheet(LABEL_STYLE)
            row.addWidget(label)
            if notice.action_text and notice.action is not None:
                button = QPushButton(notice.action_text)
                button.setProperty("class", "plugin-setup-button")
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.clicked.connect(notice.action)
                row.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
            self.notices_box.addWidget(frame)

    def show_skipped(self) -> None:
        if self._render is None or self._session is None:
            return
        layers = self._session.layers()
        lines = []
        for op in layers.all_ops():
            if op.uid in self._render.skipped_ops:
                lines.append(
                    f"{op.op} · {S.pretty_key(getattr(op, 'target', '') or '')}".strip(
                        " ·"
                    )
                )
        show_list(
            self,
            S.NOTICE_TEMPLATE_UPDATED_ACTION,
            S.NOTICE_SKIPPED_DETAIL.format(items="\n".join(lines) or "—"),
        )

    # ── Edits ──

    def _after_edit(self, select: str | None = None) -> None:
        if select is not None:
            self._pending_select = select
        self._update_history_buttons()
        self._invalidate()

    def _on_gesture(self, gesture: dict) -> None:
        if self._session is None:
            return
        info = self._slot_info(gesture["target"])
        if info is None or not info.movable:
            return
        if gesture["gesture"] == "move":
            self._session.move(gesture["target"], gesture["dx"], gesture["dy"])
        elif gesture["gesture"] == "resize" and info.resizable:
            self._session.resize(
                gesture["target"],
                gesture["width"],
                gesture["height"],
                gesture.get("dx", 0.0),
                gesture.get("dy", 0.0),
            )
        else:
            return
        self._after_edit()

    def _on_nudge(self, target: str, dx: int, dy: int) -> None:
        if self._session is None:
            return
        info = self._slot_info(target)
        if info is None or not info.movable:
            return
        self._session.move(target, dx, dy, coalesce=True)
        self._after_edit()

    def _on_position_edited(self) -> None:
        info = self._slot_info(self._selected)
        if (
            self._session is None
            or info is None
            or info.bbox is None
            or not info.movable
        ):
            return
        dx = self.spin_x.value() - info.bbox.x
        dy = self.spin_y.value() - info.bbox.y
        if round(dx) or round(dy):
            self._session.move(info.target, round(dx, 1), round(dy, 1))
            self._after_edit()

    def _on_size_edited(self) -> None:
        info = self._slot_info(self._selected)
        if (
            self._session is None
            or info is None
            or info.bbox is None
            or not info.resizable
        ):
            return
        width, height = self.spin_w.value(), self.spin_h.value()
        if width < 4 or height < 4:
            return
        if round(width - info.bbox.width) or round(height - info.bbox.height):
            self._session.resize(info.target, float(width), float(height))
            self._after_edit()

    def hide_selected(self) -> None:
        if self._selected:
            self._hide_target(self._selected)

    def _hide_target(self, target: str) -> None:
        info = self._slot_info(target)
        if (
            self._session is None
            or info is None
            or self._render is None
            or not self._render.supported
        ):
            return
        if info.added_uid:
            self._session.remove_added(info.added_uid)
            self._selected = None
        elif info.hidden:
            self._session.show(target)
        else:
            self._session.hide(target)
        self._after_edit()

    def undo_changes_to_selected(self) -> None:
        info = self._slot_info(self._selected)
        if self._session is None or info is None:
            return
        if self._session.undo_changes_to(info.target) is not None:
            self._after_edit()

    def add_modifier_box(self) -> None:
        info = self._slot_info(self._selected)
        if self._session is None or self._render is None:
            return
        if info is None:
            self._set_status(S.SELECT_A_CONTROL_FIRST)
            return
        if info.role == "note" or not info.input_key:
            self._set_status(S.NOTES_NEED_NO_PARENT)
            return
        parent_target = info.parent if info.added_uid and info.parent else None
        if parent_target is None:
            parent_target = self._parent_target_for(info)
        parent = self._slot_info(parent_target)
        if parent is None or parent.bbox is None:
            self._set_status(S.SELECT_A_CONTROL_FIRST)
            return
        entry = self.current_diagram()
        scene = self._scenes.scene_for(entry.template)
        rect = plan_one_box(scene, self._render, parent.target)
        if rect is None:
            self._set_status(S.NO_ROOM_FOR_BOX.format(name=S.pretty_key(parent.key)))
            return
        index = next_box_index(self._render, info.input_key)
        op = self._session.add_modifier_box(
            parent.target,
            index,
            round(rect.x - parent.bbox.x, 2),
            round(rect.y - parent.bbox.y, 2),
            round(rect.width, 2),
            round(rect.height, 2),
        )
        self._after_edit(select=op.uid)

    def _parent_target_for(self, info: LayoutSlotInfo) -> str | None:
        """The primary (action) slot of the input ``info`` belongs to."""
        if info.role == "action":
            return info.target
        if self._render is None:
            return None
        for slot in self._render.slots:
            if (
                slot.role == "action"
                and slot.input_key == info.input_key
                and not slot.added_uid
            ):
                return slot.target
        return None

    def add_note(self) -> None:
        if self._session is None or self._render is None or self._render.page is None:
            return
        dialog = NoteDialog(S.NOTE_DEFAULT_TEXT, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        page = self._render.page
        op = self._session.add_note(
            dialog.text() or S.NOTE_DEFAULT_TEXT,
            round(page.x + NOTE_MARGIN, 1),
            round(page.y + page.height - NOTE_HEIGHT - NOTE_MARGIN, 1),
            NOTE_WIDTH,
            NOTE_HEIGHT,
        )
        self._after_edit(select=op.uid)

    def _edit_note(self, uid: str) -> None:
        info = self._slot_info(uid)
        if self._session is None or info is None or info.role != "note":
            return
        dialog = NoteDialog(info.text, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.text() != info.text:
            self._session.edit_note(uid, dialog.text())
            self._after_edit()

    def undo(self) -> None:
        if self._page_mode:
            self.undo_page_change()
            return
        if self._session is not None and self._session.undo() is not None:
            self._after_edit()

    def redo(self) -> None:
        if self._page_mode:
            self.redo_page_change()
            return
        if self._session is not None and self._session.redo() is not None:
            self._after_edit()

    def undo_profile_changes(self) -> None:
        if self._session is None or self._export_device is None:
            return
        profile_key = self._export_device.profile_wrapper.profile_key
        name = self.profile_name
        if self._session.change_count(profile_key) == 0:
            self._set_status(S.NOTHING_FOR_PROFILE.format(profile=name))
            return
        if (
            confirm(
                self,
                S.UNDO_PROFILE_TITLE.format(profile=name),
                S.UNDO_PROFILE_TEXT.format(profile=name),
                S.UNDO_PROFILE_CONFIRM,
                S.CANCEL,
            )
            and self._session.clear_layer(profile_key) is not None
        ):
            self._after_edit()

    def reset_all(self) -> None:
        if self._session is None:
            return
        if not self._session.has_changes():
            self._set_status(S.NOTHING_TO_RESET)
            return
        if (
            confirm(
                self,
                S.RESET_ALL_TITLE,
                S.RESET_ALL_TEXT,
                S.RESET_ALL_CONFIRM,
                S.CANCEL,
            )
            and self._session.reset_all() is not None
        ):
            self._after_edit()

    # ── Auto-add ──

    def open_auto_add(self) -> None:
        from joystick_diagrams.ui.layout_auto_add_dialog import AutoAddDialog

        entry = self.current_diagram()
        if (
            entry is None
            or self._session is None
            or self._render is None
            or self._export_device is None
        ):
            return
        dialog = AutoAddDialog(
            scene=self._scenes.scene_for(entry.template),
            render=self._render,
            export_device=self._export_device,
            all_devices=[ed.device for ed in entry.export_devices],
            scope_text=(
                S.SCOPE_ONLY_PROFILE.format(profile=self.profile_name)
                if self.scope_layer
                else S.SCOPE_ALL_PROFILES
            ),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.apply_auto_add(dialog.result_ops(), dialog.list_extras_under_text())

    def apply_auto_add(self, ops: list, list_extras: bool) -> None:
        if self._session is None or not ops:
            return
        if list_extras and not modifiers_in_main_text(get_modifier_display()):
            set_modifier_display(ModifierDisplay.UNDER_MAIN_TEXT)
        self._session.apply(list(ops), label="auto-add")
        self._after_edit()

    # ── Save as new template ──

    def save_as_template(self) -> None:
        from joystick_diagrams.ui.layout_save_template_dialog import SaveTemplateDialog

        entry = self.current_diagram()
        if entry is None or self._session is None:
            return
        dialog = SaveTemplateDialog(
            template=entry.template,
            session=self._session,
            export_device=self._export_device,
            device_name=entry.device_name,
            device_id=entry.device_id,
            theme=self.appState.theme_service.resolved_active(),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.assigned:
            self._signature = None
            self.devices_changed.emit()
            self.refresh()
        if dialog.result_text:
            self._set_status(dialog.result_text)

    # ── Navigation from other screens ──

    def show_device(self, device_id: str | None) -> None:
        """Select ``device_id``'s diagram (used by "Edit layout ›"); a controller
        without a template is selected greyed, with Choose template…."""
        self._reload_diagrams()
        if device_id:
            index = self.diagram_combo.findData(device_id)
            if index < 0:
                index = self.diagram_combo.findData(ENTRY_PREFIX_NEEDS + device_id)
            if index >= 0 and index != self.diagram_combo.currentIndex():
                self.diagram_combo.setCurrentIndex(index)
        self._invalidate()


def _leading_int(text: str) -> int:
    digits = ""
    for char in text.strip():
        if char.isdigit():
            digits += char
        else:
            break
    return int(digits) if digits else 1


def render_context_for_editor() -> RenderContext:
    return dataclasses.replace(build_render_context(), preview=True)


if __name__ == "__main__":
    pass
