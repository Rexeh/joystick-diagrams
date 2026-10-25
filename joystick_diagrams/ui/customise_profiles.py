"""3. Bindings › Bindings: which action is on each control (journey board J07).

Opens on a controller: the **Controller** picker lists the Ready controllers
plus "All controllers (by profile)" (the profile-first tree, every controller
of the chosen profile under its own heading). The **Profile** picker lists only
the profiles with bindings on the chosen controller, with a count.

The tree has three columns, Control · Action · Modifier. Modifier rows carry
chips coloured by key group (``modifier_identity`` styles, black text on the
Okabe-Ito fills). A binding that comes from another profile ("Shared
bindings") says so: ``(from "DCS World / Common")``, and selecting it shows a
link that opens Shared bindings on that profile.

Labels: double-click an action, select it and press F2, or press **Edit
label**. The editor starts on the current label (or the game's text); an empty
text or the game's own text removes the label. Labels are global: every row
with the same action updates at once. There is no "Hide" here; whether a
controller gets a diagram is decided in 2. Controllers.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import qtawesome as qta
from PySide6.QtCore import QEvent, QModelIndex, QObject, QRect, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QIcon, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.input.axis import Axis, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat
from joystick_diagrams.template_catalog import control_label
from joystick_diagrams.ui import strings_bindings as S

_logger = logging.getLogger(__name__)

CUSTOM_LABEL_COLOR = QColor("#34D399")
DEFAULT_TEXT_COLOR = QColor("#E8EAED")
MUTED_TEXT_COLOR = QColor("#9AA0A6")
ORIGINAL_COMMAND_ROLE = Qt.ItemDataRole.UserRole
INHERITED_FROM_ROLE = Qt.ItemDataRole.UserRole + 1  # (profile_key, display name)
CHIPS_ROLE = Qt.ItemDataRole.UserRole + 2  # list[(text, fill colour)]
DEVICE_GUID_ROLE = Qt.ItemDataRole.UserRole + 3

ALL_CONTROLLERS = ""  # the "All controllers (by profile)" entry
COLUMN_CONTROL = 0
COLUMN_ACTION = 1
COLUMN_MODIFIER = 2
CHIP_FALLBACK_FILL = "#BDC1C6"

# Dot colours per control type
TYPE_DOT_COLORS = {
    Button: "#16a085",  # teal
    Axis: "#2980b9",  # blue
    Hat: "#5865F2",  # indigo
    AxisSlider: "#2980b9",  # blue (same as axis)
}
MOD_DOT_COLOR = "#E67E22"  # warm amber


# ── Data (pure, testable) ──


def profile_display_name(wrapper: Any) -> str:
    return f"{wrapper.profile_origin.name} / {wrapper.profile_name}"


def binding_count(device: Any) -> int:
    """Actions bound on a controller: each control's action plus each modifier binding."""
    if device is None:
        return 0
    count = 0
    for input_obj in device.get_combined_inputs().values():
        if (input_obj.command or "").strip():
            count += 1
        count += sum(1 for m in input_obj.modifiers if (m.command or "").strip())
    return count


def profiles_using(guid: str, profile_wrappers: Iterable[Any]) -> list[tuple[Any, int]]:
    """``(wrapper, binding count)`` for every profile with bindings on ``guid``."""
    found: list[tuple[Any, int]] = []
    for wrapper in profile_wrappers:
        devices = getattr(wrapper.profile, "devices", None) or {}
        count = binding_count(devices.get(guid))
        if count:
            found.append((wrapper, count))
    return found


def ready_controllers(profile_wrappers: list[Any], statuses: dict | None = None):
    """``[(guid, name)]`` of the controllers that get a diagram, by name."""
    if statuses is None:
        try:
            from joystick_diagrams.device_status import all_device_statuses

            statuses = all_device_statuses(profile_wrappers, include_unseen=False)
        except Exception as error:  # noqa: BLE001 - the picker still offers "All"
            _logger.warning(f"Could not work out controller statuses: {error}")
            statuses = {}
    ready = [
        (guid, info.name or guid)
        for guid, info in statuses.items()
        if info.state.exports
    ]
    return sorted(ready, key=lambda item: item[1].casefold())


def _natural_key(identifier: str) -> tuple:
    parts = identifier.lower().split("_")
    order = {"button": 0, "pov": 1, "axis": 2}.get(parts[0], 3)
    number = next((int(p) for p in parts[1:] if p.isdigit()), 0)
    return (order, number, identifier.lower())


@dataclass
class ModifierRow:
    keys: tuple[str, ...]
    command: str
    inherited_from: tuple[str, str] | None = None  # (profile_key, display name)


@dataclass
class BindingRow:
    identifier: str
    control_type: type
    command: str
    modifiers: list[ModifierRow] = field(default_factory=list)
    inherited_from: tuple[str, str] | None = None

    @property
    def control_text(self) -> str:
        return control_label(self.identifier)


def _parent_source(
    wrapper: Any, guid: str, identifier: str, command: str, keys: frozenset | None
) -> tuple[str, str] | None:
    """The parent profile whose own bindings hold ``command`` (``None`` when not found)."""
    for parent in getattr(wrapper, "parents", None) or []:
        devices = getattr(parent.original_profile, "devices", None) or {}
        device = devices.get(guid)
        if device is None:
            continue
        found = device.get_combined_inputs().get(identifier)
        if found is None:
            continue
        if keys is None and found.command == command:
            return (parent.profile_key, profile_display_name(parent))
        if keys is not None and any(
            frozenset(m.modifiers) == keys and m.command == command
            for m in found.modifiers
        ):
            return (parent.profile_key, profile_display_name(parent))
    return None


def binding_rows(wrapper: Any, guid: str) -> list[BindingRow]:
    """The controller's bindings in ``wrapper`` (after Shared bindings), with sources."""
    devices = getattr(wrapper.profile, "devices", None) or {}
    device = devices.get(guid)
    if device is None:
        return []
    own_devices = getattr(wrapper.original_profile, "devices", None) or {}
    own_device = own_devices.get(guid)
    own_inputs = own_device.get_combined_inputs() if own_device is not None else {}
    has_parents = bool(getattr(wrapper, "parents", None))

    rows: list[BindingRow] = []
    for identifier, input_obj in device.get_combined_inputs().items():
        own = own_inputs.get(identifier)
        source = None
        if has_parents and (own is None or own.command != input_obj.command):
            source = _parent_source(wrapper, guid, identifier, input_obj.command, None)
        row = BindingRow(
            identifier,
            type(input_obj.input_control),
            input_obj.command,
            inherited_from=source,
        )
        own_modifiers = (
            {(frozenset(m.modifiers), m.command) for m in own.modifiers}
            if own is not None
            else set()
        )
        for modifier in input_obj.modifiers:
            keys = frozenset(modifier.modifiers)
            mod_source = None
            if has_parents and (keys, modifier.command) not in own_modifiers:
                mod_source = _parent_source(
                    wrapper, guid, identifier, modifier.command, keys
                )
            row.modifiers.append(
                ModifierRow(modifier.sorted_keys, modifier.command, mod_source)
            )
        rows.append(row)
    rows.sort(key=lambda r: _natural_key(r.identifier))
    return rows


def chip_colours(keys: Iterable[str]) -> list[tuple[str, str]]:
    """``(key text, fill)`` per modifier key, coloured by its key group."""
    try:
        from joystick_diagrams.modifier_identity import resolve_key

        snapshot = AppState().modifier_key_service.snapshot()
    except Exception:  # noqa: BLE001 - chips fall back to grey
        snapshot = None
    chips: list[tuple[str, str]] = []
    for key in keys:
        fill = CHIP_FALLBACK_FILL
        if snapshot is not None:
            try:
                resolved = resolve_key(key, snapshot)
                if resolved.style is not None and resolved.style.colour:
                    fill = resolved.style.colour
            except Exception:  # noqa: BLE001
                pass
        chips.append((key, fill))
    return chips


# ── Delegates ──


class ChipDelegate(QStyledItemDelegate):
    """Paints the Modifier column as rounded chips (black text on the key colour)."""

    PAD_X = 6
    GAP = 4

    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
        chips = index.data(CHIPS_ROLE)
        if not chips:
            super().paint(painter, option, index)
            return
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        style = opt.widget.style() if opt.widget is not None else None
        if style is not None:
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont(option.font)
        font.setPointSizeF(max(font.pointSizeF() - 1, 7))
        font.setBold(True)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        height = metrics.height() + 4
        x = option.rect.left() + 4
        y = option.rect.top() + (option.rect.height() - height) // 2
        for text, fill in chips:
            width = metrics.horizontalAdvance(text) + 2 * self.PAD_X
            rect = QRect(x, y, width, height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(fill))
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QColor("#000000"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            x += width + self.GAP
        painter.restore()

    def sizeHint(self, option, index: QModelIndex) -> QSize:  # noqa: N802
        hint = super().sizeHint(option, index)
        chips = index.data(CHIPS_ROLE)
        if chips:
            metrics = QFontMetrics(option.font)
            width = sum(
                metrics.horizontalAdvance(t) + 2 * self.PAD_X + self.GAP
                for t, _ in chips
            )
            hint.setWidth(max(hint.width(), width + 8))
        return hint


class LabelDelegate(QStyledItemDelegate):
    """Edits the Action column as a label: starts on the label (or the game's text)
    and hands the result to ``commit`` instead of writing the cell."""

    def __init__(self, commit, parent: QObject | None = None):
        super().__init__(parent)
        self._commit = commit

    def createEditor(self, parent, option, index):  # noqa: N802
        editor = QLineEdit(parent)
        editor.setAccessibleName(S.EDIT_LABEL)
        return editor

    def setEditorData(self, editor, index):  # noqa: N802
        original = index.data(ORIGINAL_COMMAND_ROLE) or ""
        try:
            editor.setText(AppState().label_service.resolve(original))
        except Exception:  # noqa: BLE001
            editor.setText(original)
        editor.selectAll()

    def setModelData(self, editor, model, index):  # noqa: N802
        self._commit(index, editor.text())


# ── Screen ──


class CustomiseProfiles(QWidget):
    """The Bindings screen of stage 3."""

    device_visibility_changed = Signal()  # kept for older callers; never emitted here
    labels_changed = Signal()
    open_shared_requested = Signal(str)  # profile key
    selection_changed = Signal()  # controller or profile picker changed

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()
        self._loading = False
        self._statuses: dict | None = None
        self._ready: list[tuple[str, str]] = []
        self._wanted_guid: str | None = None
        self._wanted_profile: str | None = None
        self._selected_source: tuple[str, str] | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Controller · Profile · Search · Edit label
        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)
        controller_label = QLabel(S.CONTROLLER)
        controller_label.setStyleSheet("font-weight: bold;")
        picker_row.addWidget(controller_label)
        self.controller_combo = QComboBox()
        self.controller_combo.setProperty("class", "view-binds-list")
        self.controller_combo.setAccessibleName(S.CONTROLLER)
        self.controller_combo.setToolTip(S.CONTROLLER_TIP)
        self.controller_combo.setMinimumWidth(220)
        self.controller_combo.setMaxVisibleItems(15)
        self.controller_combo.currentIndexChanged.connect(self._on_controller_changed)
        picker_row.addWidget(self.controller_combo, 2)
        picker_row.addSpacing(8)
        profile_label = QLabel(S.PROFILE)
        profile_label.setStyleSheet("font-weight: bold;")
        picker_row.addWidget(profile_label)
        self.profile_combo = QComboBox()
        self.profile_combo.setProperty("class", "view-binds-list")
        self.profile_combo.setAccessibleName(S.PROFILE)
        self.profile_combo.setToolTip(S.PROFILE_TIP)
        self.profile_combo.setMinimumWidth(220)
        self.profile_combo.setMaxVisibleItems(15)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        picker_row.addWidget(self.profile_combo, 2)
        picker_row.addSpacing(8)
        self.binds_search = QLineEdit()
        self.binds_search.setPlaceholderText(S.SEARCH_PLACEHOLDER)
        self.binds_search.setAccessibleName(S.SEARCH_ACCESSIBLE)
        self.binds_search.setProperty("class", "binds-search")
        self.binds_search.setClearButtonEnabled(True)
        self.binds_search.addAction(
            qta.icon("fa5s.search", color="#9AA0A6"),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.binds_search.textChanged.connect(self._filter_binds_tree)
        picker_row.addWidget(self.binds_search, 1)
        self.edit_label_button = QPushButton(S.EDIT_LABEL)
        self.edit_label_button.setIcon(qta.icon("fa5s.pen", color="white"))
        self.edit_label_button.setIconSize(QSize(12, 12))
        self.edit_label_button.setProperty("class", "plugin-setup-button")
        self.edit_label_button.setToolTip(S.EDIT_LABEL_TIP)
        self.edit_label_button.clicked.connect(self.edit_current_label)
        self.edit_label_button.setEnabled(False)
        picker_row.addWidget(self.edit_label_button)
        root.addLayout(picker_row)

        # Tree: Control · Action · Modifier
        self.viewBindsTreeWidget = QTreeWidget()
        self.viewBindsTreeWidget.setProperty("class", "view-binds-tree")
        self.viewBindsTreeWidget.setColumnCount(3)
        self.viewBindsTreeWidget.setHeaderLabels(
            [S.COLUMN_CONTROL, S.COLUMN_ACTION, S.COLUMN_MODIFIER]
        )
        header = self.viewBindsTreeWidget.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(COLUMN_CONTROL, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(COLUMN_ACTION, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COLUMN_MODIFIER, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(COLUMN_CONTROL, 170)
        header.resizeSection(COLUMN_MODIFIER, 170)
        header.setMinimumSectionSize(80)
        self.viewBindsTreeWidget.setIconSize(QSize(10, 10))
        self.viewBindsTreeWidget.setWordWrap(False)
        self.viewBindsTreeWidget.setUniformRowHeights(True)
        self.viewBindsTreeWidget.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.viewBindsTreeWidget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.viewBindsTreeWidget.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._label_delegate = LabelDelegate(self._commit_label, self)
        self.viewBindsTreeWidget.setItemDelegateForColumn(
            COLUMN_ACTION, self._label_delegate
        )
        self.viewBindsTreeWidget.setItemDelegateForColumn(
            COLUMN_MODIFIER, ChipDelegate(self)
        )
        self.viewBindsTreeWidget.itemDoubleClicked.connect(self._on_double_clicked)
        self.viewBindsTreeWidget.currentItemChanged.connect(self._on_current_changed)
        self.viewBindsTreeWidget.installEventFilter(self)
        self.viewBindsTreeWidget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.viewBindsTreeWidget.customContextMenuRequested.connect(
            self.show_context_menu
        )
        self.empty_label = QLabel()
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("color: #9AA0A6; padding: 20px;")
        # Tree and empty state share the stretching slot (nothing else moves)
        self.tree_stack = QStackedWidget()
        self.tree_stack.addWidget(self.viewBindsTreeWidget)
        self.tree_stack.addWidget(self.empty_label)
        root.addWidget(self.tree_stack, 1)

        # "This binding comes from …" · Open Shared bindings
        self.source_row = QWidget()
        source_layout = QHBoxLayout(self.source_row)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.setSpacing(8)
        self.source_label = QLabel()
        self.source_label.setObjectName("device_help_label")
        source_layout.addWidget(self.source_label)
        self.open_shared_button = QPushButton(S.OPEN_SHARED + " ›")
        self.open_shared_button.setFlat(True)
        self.open_shared_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_shared_button.setStyleSheet(
            "QPushButton { color: #8AB4F8; border: none; background: transparent; "
            "padding: 0; text-align: left; text-transform: none; } QPushButton:hover { text-decoration: underline; }"
        )
        self.open_shared_button.clicked.connect(self._open_shared)
        source_layout.addWidget(self.open_shared_button)
        source_layout.addStretch(1)
        self.source_row.hide()
        root.addWidget(self.source_row)

        self.hint_label = QLabel(S.RELABEL_HINT)
        self.hint_label.setObjectName("device_help_label")
        self.hint_label.setWordWrap(True)
        root.addWidget(self.hint_label)

        self.device_icon = qta.icon("fa5s.gamepad", color="#9AA0A6")

    # ── Refresh ──

    def get_profiles(self) -> list[Any]:
        return list(self.appState.profile_wrappers)

    def refresh(self, statuses: dict | None = None) -> None:
        """Reload the pickers and the tree (keeps the controller and profile chosen)."""
        self._statuses = statuses
        wrappers = self.get_profiles()
        self._ready = ready_controllers(wrappers, statuses)
        wanted = self._wanted_guid
        if wanted is None:
            wanted = self.current_controller()
        if wanted is None:
            wanted = self._ready[0][0] if self._ready else ALL_CONTROLLERS
        self._loading = True
        try:
            self.controller_combo.clear()
            for guid, name in self._ready:
                self.controller_combo.addItem(name, guid)
            self.controller_combo.addItem(S.ALL_CONTROLLERS, ALL_CONTROLLERS)
            index = self.controller_combo.findData(wanted)
            self.controller_combo.setCurrentIndex(
                index if index >= 0 else self.controller_combo.count() - 1
            )
        finally:
            self._loading = False
        self._wanted_guid = None
        self._reload_profiles()

    def current_controller(self) -> str | None:
        if self.controller_combo.count() == 0:
            return None
        return self.controller_combo.currentData()

    def current_profile(self) -> Any:
        return self.profile_combo.currentData()

    def current_profile_key(self) -> str | None:
        wrapper = self.current_profile()
        return wrapper.profile_key if wrapper is not None else None

    def select_controller(self, guid: str | None) -> None:
        """Open on ``guid`` (a deep link from 2. Controllers › View bindings)."""
        if guid is None:
            return
        index = self.controller_combo.findData(guid)
        if index < 0:
            self._wanted_guid = guid
            index = self.controller_combo.findData(ALL_CONTROLLERS)
        if index >= 0:
            self.controller_combo.setCurrentIndex(index)

    def select_profile(self, profile_key: str | None) -> None:
        if not profile_key:
            return
        for index in range(self.profile_combo.count()):
            wrapper = self.profile_combo.itemData(index)
            if wrapper is not None and wrapper.profile_key == profile_key:
                self.profile_combo.setCurrentIndex(index)
                return

    def _on_controller_changed(self, _index: int) -> None:
        if self._loading:
            return
        self._reload_profiles()
        self.selection_changed.emit()

    def _reload_profiles(self) -> None:
        guid = self.current_controller()
        wanted = self._wanted_profile or self.current_profile_key()
        wrappers = self.get_profiles()
        self._loading = True
        try:
            self.profile_combo.clear()
            if guid:
                entries = profiles_using(guid, wrappers)
            else:
                entries = [
                    (w, sum(binding_count(d) for d in w.profile.devices.values()))
                    for w in wrappers
                ]
            for wrapper, count in entries:
                self.profile_combo.addItem(
                    QIcon(wrapper.profile_origin.icon),
                    S.PROFILE_ENTRY.format(
                        game=wrapper.profile_origin.name,
                        profile=wrapper.profile_name,
                        count=count,
                        bindings=S.plural(count, *S.BINDINGS),
                    ),
                    wrapper,
                )
            index = -1
            if wanted:
                for i in range(self.profile_combo.count()):
                    if self.profile_combo.itemData(i).profile_key == wanted:
                        index = i
                        break
            if self.profile_combo.count():
                self.profile_combo.setCurrentIndex(max(index, 0))
        finally:
            self._loading = False
        self._wanted_profile = None
        self._load_tree()

    def _on_profile_changed(self, _index: int) -> None:
        if self._loading:
            return
        self._load_tree()
        self.selection_changed.emit()

    # ── Tree ──

    def _dot_icon(self, color: str) -> QIcon:
        return qta.icon("fa5s.circle", color=color)

    def _show_empty(self, text: str | None) -> None:
        self.empty_label.setText(text or "")
        self.tree_stack.setCurrentWidget(
            self.empty_label if text else self.viewBindsTreeWidget
        )

    def _load_tree(self) -> None:
        self.binds_search.blockSignals(True)
        self.binds_search.clear()
        self.binds_search.blockSignals(False)
        tree = self.viewBindsTreeWidget
        tree.blockSignals(True)
        tree.clear()
        tree.blockSignals(False)
        self._selected_source = None
        self.source_row.hide()
        self.edit_label_button.setEnabled(False)

        wrappers = self.get_profiles()
        if not wrappers:
            self._show_empty(S.EMPTY)
            return
        wrapper = self.current_profile()
        guid = self.current_controller()
        if wrapper is None:
            name = self.controller_combo.currentText()
            self._show_empty(S.NO_PROFILES_FOR_CONTROLLER.format(controller=name))
            return
        self._show_empty(None)
        if guid:
            for row in binding_rows(wrapper, guid):
                self._add_binding(tree.invisibleRootItem(), row)
            return
        self._load_all_controllers(wrapper)

    def _load_all_controllers(self, wrapper: Any) -> None:
        """The profile-first tree: every controller of ``wrapper`` under a heading."""
        service = self.appState.device_service
        devices = sorted(
            wrapper.profile.get_devices().values(),
            key=lambda d: service.resolve_name(d.guid, d.name).casefold(),
        )
        for device_obj in devices:
            name = service.resolve_name(device_obj.guid, device_obj.name)
            no_diagram = self._is_no_diagram(device_obj.guid)
            root = QTreeWidgetItem(self.viewBindsTreeWidget)
            rows = binding_rows(wrapper, device_obj.guid)
            text = name
            if not rows:
                text = f"{name} · {S.NOTHING_BOUND}"
            elif no_diagram:
                text = f"{name} · {S.NO_DIAGRAM_SUFFIX}"
            root.setText(COLUMN_CONTROL, text)
            root.setIcon(COLUMN_CONTROL, self.device_icon)
            root.setData(COLUMN_CONTROL, DEVICE_GUID_ROLE, device_obj.guid)
            root.setFirstColumnSpanned(True)
            if no_diagram or not rows:
                root.setForeground(COLUMN_CONTROL, QBrush(MUTED_TEXT_COLOR))
            for row in rows:
                self._add_binding(root, row, dimmed=no_diagram)
            root.setExpanded(True)

    def _is_no_diagram(self, guid: str) -> bool:
        info = (self._statuses or {}).get(guid)
        if info is not None:
            return info.state.value == "no_diagram"
        try:
            return self.appState.device_service.is_hidden(guid)
        except Exception:  # noqa: BLE001
            return False

    def _add_binding(
        self, parent: QTreeWidgetItem, row: BindingRow, dimmed: bool = False
    ) -> None:
        node = QTreeWidgetItem(parent)
        node.setIcon(
            COLUMN_CONTROL,
            self._dot_icon(TYPE_DOT_COLORS.get(row.control_type, "#9AA0A6")),
        )
        node.setText(COLUMN_CONTROL, row.control_text)
        node.setToolTip(COLUMN_CONTROL, row.control_text)
        self._set_action(node, row.command, row.inherited_from)
        if dimmed:
            node.setForeground(COLUMN_CONTROL, QBrush(MUTED_TEXT_COLOR))
        for modifier in row.modifiers:
            child = QTreeWidgetItem(node)
            child.setIcon(COLUMN_CONTROL, self._dot_icon(MOD_DOT_COLOR))
            self._set_action(child, modifier.command, modifier.inherited_from)
            keys_text = " ".join(modifier.keys)
            child.setText(COLUMN_MODIFIER, keys_text)
            child.setToolTip(COLUMN_MODIFIER, " + ".join(modifier.keys))
            child.setData(COLUMN_MODIFIER, CHIPS_ROLE, chip_colours(modifier.keys))
        node.setExpanded(True)

    def _action_text(self, original: str, source: tuple[str, str] | None) -> str:
        label = self.appState.label_service.resolve(original)
        text = original
        if label != original:
            text = f"{original}   {S.SHOWN_AS.format(label=label)}"
        if source is not None:
            text += f" ({S.INHERITED_FROM.format(profile=source[1])})"
        return text

    def _set_action(
        self, node: QTreeWidgetItem, original: str, source: tuple[str, str] | None
    ) -> None:
        node.setData(COLUMN_ACTION, ORIGINAL_COMMAND_ROLE, original)
        node.setData(COLUMN_ACTION, INHERITED_FROM_ROLE, source)
        node.setText(COLUMN_ACTION, self._action_text(original, source))
        node.setToolTip(COLUMN_ACTION, S.GAME_TEXT_TIP.format(action=original))
        node.setFlags(node.flags() | Qt.ItemFlag.ItemIsEditable)
        self._set_custom_label_indicator(node, original)

    def _set_custom_label_indicator(self, item: QTreeWidgetItem, original: str):
        if self.appState.label_service.has_custom_label(original):
            item.setForeground(COLUMN_ACTION, QBrush(CUSTOM_LABEL_COLOR))
        else:
            item.setForeground(COLUMN_ACTION, QBrush(DEFAULT_TEXT_COLOR))

    def _update_all_matching_items(self, original: str):
        """Every row with the same action shows the new label (labels are global)."""
        iterator = QTreeWidgetItemIterator(self.viewBindsTreeWidget)
        while iterator.value():
            node = iterator.value()
            if node.data(COLUMN_ACTION, ORIGINAL_COMMAND_ROLE) == original:
                source = node.data(COLUMN_ACTION, INHERITED_FROM_ROLE)
                node.setText(COLUMN_ACTION, self._action_text(original, source))
                self._set_custom_label_indicator(node, original)
            iterator += 1

    def _filter_binds_tree(self, text: str):
        """Hide rows that match neither the control, the action nor a modifier."""
        query = text.lower().strip()
        tree = self.viewBindsTreeWidget

        def matches(item: QTreeWidgetItem) -> bool:
            return any(query in item.text(col).lower() for col in range(3))

        def apply(item: QTreeWidgetItem) -> bool:
            """Returns True when ``item`` or a child is visible."""
            if item.data(COLUMN_CONTROL, DEVICE_GUID_ROLE):
                any_visible = False
                for i in range(item.childCount()):
                    any_visible = apply(item.child(i)) or any_visible
                item.setHidden(bool(query) and not any_visible)
                return any_visible
            visible = not query or matches(item)
            child_match = False
            for i in range(item.childCount()):
                child = item.child(i)
                child_visible = not query or matches(child) or visible
                child.setHidden(not child_visible)
                child_match = child_match or (bool(query) and matches(child))
            visible = visible or child_match
            item.setHidden(not visible)
            return visible

        any_shown = False
        for i in range(tree.topLevelItemCount()):
            any_shown = apply(tree.topLevelItem(i)) or any_shown
        if query and not any_shown and tree.topLevelItemCount():
            self._show_empty(S.NO_MATCH.format(query=text.strip()))
        elif tree.topLevelItemCount():
            self._show_empty(None)

    # ── Labels ──

    def _editable(self, item: QTreeWidgetItem | None) -> bool:
        return (
            item is not None
            and item.data(COLUMN_ACTION, ORIGINAL_COMMAND_ROLE) is not None
        )

    def edit_current_label(self) -> None:
        item = self.viewBindsTreeWidget.currentItem()
        if self._editable(item):
            self.viewBindsTreeWidget.setCurrentItem(item, COLUMN_ACTION)
            self.viewBindsTreeWidget.editItem(item, COLUMN_ACTION)

    def _on_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._editable(item):
            self.viewBindsTreeWidget.editItem(item, COLUMN_ACTION)

    def eventFilter(self, watched, event):  # noqa: N802
        if (
            watched is self.viewBindsTreeWidget
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_F2
            and self.viewBindsTreeWidget.state() != QAbstractItemView.State.EditingState
        ):
            self.edit_current_label()
            return True
        return super().eventFilter(watched, event)

    def _commit_label(self, index: QModelIndex, text: str) -> None:
        original = index.data(ORIGINAL_COMMAND_ROLE)
        if original is None:
            return
        self.set_label(original, text)

    def set_label(self, original: str, text: str) -> None:
        """Store ``text`` as the label for ``original`` (empty or same: remove it)."""
        new_text = text.strip()
        if not new_text or new_text == original:
            self.appState.label_service.remove_label(original)
        else:
            self.appState.label_service.set_label(original, new_text)
        self._update_all_matching_items(original)
        self.labels_changed.emit()

    def _on_current_changed(self, current: QTreeWidgetItem | None, _previous) -> None:
        self.edit_label_button.setEnabled(self._editable(current))
        source = (
            current.data(COLUMN_ACTION, INHERITED_FROM_ROLE)
            if current is not None
            else None
        )
        self._selected_source = source
        if source:
            self.source_label.setText(S.INHERITED_NOTE.format(profile=source[1]))
            self.source_row.show()
        else:
            self.source_row.hide()

    def _open_shared(self) -> None:
        if self._selected_source:
            self.open_shared_requested.emit(self.current_profile_key() or "")

    # ── Context menu ──

    def show_context_menu(self, position):
        item = self.viewBindsTreeWidget.itemAt(position)
        if not self._editable(item):
            return
        original = item.data(COLUMN_ACTION, ORIGINAL_COMMAND_ROLE)
        menu = QMenu(self)
        edit_action = menu.addAction(S.EDIT_LABEL)
        reset_action = menu.addAction(S.USE_GAME_TEXT)
        reset_action.setEnabled(self.appState.label_service.has_custom_label(original))
        shared_action = None
        if item.data(COLUMN_ACTION, INHERITED_FROM_ROLE):
            menu.addSeparator()
            shared_action = menu.addAction(S.OPEN_SHARED)
        action = menu.exec(self.viewBindsTreeWidget.viewport().mapToGlobal(position))
        if action == edit_action:
            self.viewBindsTreeWidget.setCurrentItem(item)
            self.viewBindsTreeWidget.editItem(item, COLUMN_ACTION)
        elif action == reset_action:
            self.set_label(original, "")
        elif shared_action is not None and action == shared_action:
            self.open_shared_requested.emit(self.current_profile_key() or "")


if __name__ == "__main__":
    pass
