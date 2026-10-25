"""The ``layout`` pipeline stage: apply layout ops to the rendered SVG and model.

``apply_layout(job)`` is installed by ``render.default_hooks()`` and runs after
slot detection and **before** the fill stage, so the boxes and notes it adds
still hold placeholder tokens that the fill, theme and modifier-presentation
stages then treat like any template slot.

What it does, in order (plan §5.4):

1. **Gate.** Layout needs ``Capability.LAYOUT`` and ``SHAPE_STYLE``. Text-only or
   degraded adapters refuse every op with ``RenderNotice.LAYOUT_UNSUPPORTED``
   (the UI shows a banner); slots are still described for the editor, all
   ``movable=False``.
2. **Fold** the layers (template then profile) with ``layout.fold_ops``.
3. **Slots**: resize (``<rect>`` + label relayout + model size; refused with a
   notice on rotated or non-rect slots), move (translate wrapper around shape
   and label of every stacked duplicate; model ``mxGeometry``), hide (wrapper
   ``display="none"``; model ``visible="0"``). Unknown targets are skipped and
   reported (``LayoutNotice.code == "slot_missing"``, ``RenderNotice.LAYOUT_OPS_SKIPPED``).
4. **Leader lines** follow (see ``layout_scene`` for the attachment rules): the
   attached end of the stroke path and its arrowhead move with the slot (or
   stay on the same relative border spot after a resize); a free terminal point
   is mirrored into the model; lines attached only to hidden slots are hidden;
   ``MoveEdgeEndOp`` deltas are added on top.
5. **Added modifier boxes** become real slots for ``KEY_MODIFIER_N`` tokens,
   cloned from the parent's look at a smaller size, with a new model cell
   (``id="jd-<uid>"``, ``jdAdded=1``) so draw.io can edit them. Dynamic
   ``AddModifierBoxesOp``s (no explicit geometry) are planned per render with
   ``auto_layout.plan_auto_add`` from the profile's actual modifier count;
   unplaced boxes are reported (``RenderNotice.BOXES_UNPLACED``).
6. **Notes** (``AddNoteOp``) become a rect + label + model text cell;
   ``PROFILE_NAME`` is rewritten to ``TEMPLATE_NAME`` so the fill resolves it.
7. **Editor annotations** (``ctx.preview``): ``data-jd-slot="key#dup"``,
   ``data-jd-role``, ``data-jd-added="<uid>"`` on shapes/labels/wrappers and
   ``data-jd-edge="<cell id>"`` on stroke paths and arrowheads.
8. Overflow is recomputed (added boxes count as template boxes) and a
   ``TEMPLATE_UPDATED`` notice is raised when the stored ``content_hash``
   differs from the template's.

The outcome is a ``LayoutResult`` on ``job.layout`` (slots with before/after
geometry, capabilities and layer attribution; edges with their attachments;
notices; skipped op uids; unplaced boxes) that ``render.editor`` turns into the
editor's ``EditorRender``.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from joystick_diagrams.render.adapters._common import (
    SVG,
    cell_origin,
    localname,
    rect_of,
)
from joystick_diagrams.render.adapters.edge_mapping import translate_path_end
from joystick_diagrams.render.auto_layout import PlanOptions, Unplaced, plan_auto_add
from joystick_diagrams.render.context import RenderNotice
from joystick_diagrams.render.layout import (
    AddedElement,
    AddModifierBoxesOp,
    EffectiveLayout,
    LayoutLayers,
    NoteStyle,
    SlotState,
    fold_ops,
    parse_target,
)
from joystick_diagrams.render.layout_elements import (
    ADDED_CELL_PREFIX,
    MIN_FONT_SIZE,
    NewCell,
    add_model_cell,
    build_note,
    clone_box,
    hide_element,
    inner_div,
    label_font_size,
    prepend_translate,
    relayout_label,
    resize_rect,
    set_cell_hidden,
    set_geometry_size,
    shift_geometry,
    shift_terminal_point,
    slot_nodes,
    text_element,
    translate_value,
    wrap_nodes,
)
from joystick_diagrams.render.layout_scene import (
    EdgeAttachment,
    GroupTransform,
    LayoutScene,
    SlotGroup,
    build_scene,
    edge_points,
    single_rect,
)
from joystick_diagrams.render.slots import (
    Capability,
    Rect,
    ShapeRef,
    Slot,
    TextTarget,
    TextTargetKind,
)
from joystick_diagrams.render.tokens import classify

if TYPE_CHECKING:
    from joystick_diagrams.render.pipeline import RenderJob

MARKER_END_DISTANCE_PX = 12.0
ROLE_FOR_CONTENT = {"full": "", "key": "_KEY", "action": "_ACTION"}
Point = tuple[float, float]


# ── Result types ──


@dataclass(frozen=True)
class LayoutNotice:
    code: str  # slot_missing | resize_refused | not_movable | layout_unsupported |
    # template_updated | box_unplaced | parent_missing
    target: str | None = None
    uid: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class LayoutSlotInfo:
    target: str
    key: str
    role: str
    input_key: str | None
    modifier_index: int | None
    original_bbox: Rect | None
    bbox: Rect | None  # after ops
    dx: float
    dy: float
    hidden: bool
    movable: bool
    resizable: bool
    rotated: bool
    stacked: int  # number of stacked duplicates in this identity
    edges: tuple[str, ...]
    layer: str | None  # "template" | "profile" | None (untouched)
    added_uid: str | None = None
    parent: str | None = None
    text: str = ""  # notes only


@dataclass(frozen=True)
class LayoutEdgeInfo:
    edge_id: str
    points: tuple[Point, ...]
    source_slot: str | None
    source_kind: str | None
    target_slot: str | None
    target_kind: str | None
    hidden: bool
    rendered: bool


@dataclass
class LayoutResult:
    supported: bool
    page: Rect
    layers: LayoutLayers
    slots: list[LayoutSlotInfo] = field(default_factory=list)
    edges: list[LayoutEdgeInfo] = field(default_factory=list)
    notices: list[LayoutNotice] = field(default_factory=list)
    skipped_ops: list[str] = field(default_factory=list)
    unplaced: list[Unplaced] = field(default_factory=list)
    added_count: int = 0


# ── Helpers ──


def _supports_layout(capabilities: frozenset[Capability]) -> bool:
    return Capability.LAYOUT in capabilities and Capability.SHAPE_STYLE in capabilities


def _top_node(node: Any) -> Any:
    """Climb out of wrappers this stage created so siblings land beside the slot."""
    while (
        node.getparent() is not None and node.getparent().get("data-jd-op") is not None
    ):
        node = node.getparent()
    return node


def _edge_markers(attachment: EdgeAttachment) -> list[Any]:
    edge = attachment.edge
    if edge.markers:
        return list(edge.markers)
    path = edge.stroke_path
    if edge.element is None or path is None or edge.element is path:
        return []
    return [
        node
        for node in edge.element.iter()
        if node is not path
        and localname(node) in ("path", "ellipse", "circle", "polygon")
    ]


def _near(element: Any, point: Point) -> bool:
    bbox = rect_of(element)
    return (
        bbox is not None
        and bbox.expanded(MARKER_END_DISTANCE_PX).distance_to_point(*point) == 0.0
    )


def _rounded(delta: Point) -> Point:
    return (round(delta[0], 2), round(delta[1], 2))


def _set_attributes(element: Any, attributes: dict[str, str]) -> None:
    for name, value in attributes.items():
        element.set(name, value)


@dataclass
class _BoxSpec:
    uid: str
    index: int
    content: str
    rect: Rect
    token: str = ""


class LayoutApplier:
    """One run of the layout stage over a ``RenderJob``."""

    def __init__(self, job: RenderJob, layers: LayoutLayers) -> None:
        assert job.doc is not None and job.model is not None and job.slots is not None
        self.job = job
        self.doc = job.doc
        self.model = job.model
        self.slot_map = job.slots
        self.layers = layers
        self.effective: EffectiveLayout = fold_ops(layers.all_ops())
        self.scene: LayoutScene = build_scene(self.slot_map, self.doc.root, self.model)
        self.result = LayoutResult(
            _supports_layout(self.slot_map.capabilities), self.scene.page, layers
        )
        self.transforms: dict[str, GroupTransform] = {}
        self.hidden: set[str] = set()
        self.hidden_edges: set[str] = set()
        self.added_rects: list[Rect] = []
        self.added_info: list[LayoutSlotInfo] = []
        self.annotations: list[tuple[Any, dict[str, str]]] = []
        self._dom_anchor: dict[str, Any] = {}  # parent target → last inserted node
        self._cell_anchor: dict[str, Any] = {}  # parent target → last inserted cell

    # ── Orchestration ──

    def run(self) -> LayoutResult:
        if not self.result.supported:
            self._refuse_all()
        else:
            self._apply_slot_states()
            self._follow_edges()
            self._add_boxes()
            self._add_notes()
        if self.job.ctx.preview:
            self._annotate()
        self._describe()
        self._check_drift()
        return self.result

    def _notice(
        self,
        code: str,
        target: str | None = None,
        uid: str | None = None,
        detail: str = "",
    ) -> None:
        self.result.notices.append(LayoutNotice(code, target, uid, detail))

    def _skip(
        self, uids: list[str], code: str, target: str | None, detail: str = ""
    ) -> None:
        for uid in uids:
            if uid not in self.result.skipped_ops:
                self.result.skipped_ops.append(uid)
        self._notice(code, target, uids[0] if uids else None, detail)
        if (
            RenderNotice.LAYOUT_OPS_SKIPPED not in self.job.notices
            and code != "layout_unsupported"
        ):
            self.job.notices.append(RenderNotice.LAYOUT_OPS_SKIPPED)

    def _refuse_all(self) -> None:
        uids = [op.uid for op in self.layers.all_ops()]
        if uids:
            self.result.skipped_ops.extend(uids)
            self._notice("layout_unsupported", detail=self.slot_map.adapter)
            self.job.notices.append(RenderNotice.LAYOUT_UNSUPPORTED)

    # ── Slots ──

    def _apply_slot_states(self) -> None:
        for target, state in self.effective.changed_slots().items():
            group = self.scene.group(target)
            if group is None:
                self._skip(state.op_uids, "slot_missing", target)
                continue
            if not group.movable:
                self._skip(state.op_uids, "not_movable", target)
                continue
            self._apply_group_state(group, state)

    def _apply_group_state(self, group: SlotGroup, state: SlotState) -> None:
        assert group.bbox is not None
        before = group.bbox
        width, height = before.width, before.height
        if state.size is not None:
            if group.resizable:
                width, height = state.size
                self._resize_group(group, width - before.width, height - before.height)
            else:
                self._skip(
                    state.op_uids[-1:],
                    "resize_refused",
                    group.target,
                    "rotated or not a rectangle",
                )
        after = Rect(before.x + state.dx, before.y + state.dy, width, height)
        self.transforms[group.target] = GroupTransform(before, after)
        if state.dx or state.dy:
            self._translate_group(group, state.dx, state.dy)
        if state.hidden:
            self._hide_group(group)

    def _resize_group(self, group: SlotGroup, dw: float, dh: float) -> None:
        for slot in group.slots:
            rect = single_rect(slot)
            if rect is not None:
                resize_rect(
                    rect,
                    float(rect.get("width") or 0) + dw,
                    float(rect.get("height") or 0) + dh,
                )
            if slot.label_group is not None:
                relayout_label(slot.label_group, dw, dh)
        for cell in group.cells:
            geometry = cell.geometry
            if geometry is not None:
                set_geometry_size(cell, geometry.width + dw, geometry.height + dh)

    def _translate_group(self, group: SlotGroup, dx: float, dy: float) -> None:
        for slot in group.slots:
            nodes = slot_nodes(slot)
            if nodes:
                wrap_nodes(
                    nodes, {"transform": translate_value(dx, dy), "data-jd-op": "move"}
                )
        for cell in group.cells:
            shift_geometry(cell, dx, dy)

    def _hide_group(self, group: SlotGroup) -> None:
        self.hidden.add(group.target)
        for slot in group.slots:
            nodes = [_top_node(node) for node in slot_nodes(slot)]
            if nodes:
                wrap_nodes(
                    list(dict.fromkeys(nodes)),
                    {"display": "none", "data-jd-op": "hide"},
                )
        for cell in group.cells:
            set_cell_hidden(cell)

    # ── Leader lines ──

    def _follow_edges(self) -> None:
        for attachment in self.scene.attachments:
            if self._edge_should_hide(attachment):
                self._hide_edge(attachment)
                continue
            for end in ("source", "target"):
                delta = self._end_delta(attachment, end)
                if delta != (0.0, 0.0):
                    self._move_edge_end(attachment, end, delta)

    def _edge_should_hide(self, attachment: EdgeAttachment) -> bool:
        groups = attachment.attached_groups()
        if not groups or not groups <= self.hidden:
            return False
        return all(
            self.effective.slots[target].hide_leaders
            for target in groups
            if target in self.effective.slots
        )

    def _hide_edge(self, attachment: EdgeAttachment) -> None:
        edge = attachment.edge
        if edge.element is not None:
            hide_element(edge.element)
        for marker in _edge_markers(attachment):
            hide_element(marker)
        if edge.cell is not None:
            set_cell_hidden(edge.cell)
        if edge.edge_id is not None:
            self.hidden_edges.add(edge.edge_id)

    def _follow_delta(self, attachment: EdgeAttachment, end: str) -> Point:
        att = attachment.end(end)
        if att.kind is None or att.point is None:
            return (0.0, 0.0)
        members = att.members if att.kind == "model" else (att.group,)
        transforms = [self.transforms.get(m) for m in members if m]
        if not transforms or any(t is None for t in transforms):
            return (0.0, 0.0)
        if len(transforms) == 1:
            new = transforms[0].map_point(att.point)
            return (new[0] - att.point[0], new[1] - att.point[1])
        deltas = {_rounded(t.delta) for t in transforms}
        return deltas.pop() if len(deltas) == 1 else (0.0, 0.0)

    def _end_delta(self, attachment: EdgeAttachment, end: str) -> Point:
        follow = self._follow_delta(attachment, end)
        manual = (0.0, 0.0)
        if attachment.edge_id is not None:
            manual = self.effective.edge_ends.get((attachment.edge_id, end), (0.0, 0.0))
        return _rounded((follow[0] + manual[0], follow[1] + manual[1]))

    def _move_edge_end(
        self, attachment: EdgeAttachment, end: str, delta: Point
    ) -> None:
        edge = attachment.edge
        path = edge.stroke_path
        point = attachment.end(end).point
        if path is not None and point is not None:
            path.set("d", translate_path_end(path.get("d"), end, *delta))
            for marker in _edge_markers(attachment):
                if _near(marker, point):
                    prepend_translate(marker, *delta)
        terminal = edge.source_id if end == "source" else edge.target_id
        if edge.cell is not None and terminal is None:
            fallback = None
            if point is not None:
                ox, oy = self.scene.offset
                gx, gy = cell_origin(edge.cell, self.scene.cells)
                fallback = (point[0] - ox - gx, point[1] - oy - gy)
            shift_terminal_point(edge.cell, end, delta, fallback)

    # ── Added modifier boxes ──

    def _current_bbox(self, group: SlotGroup) -> Rect | None:
        transform = self.transforms.get(group.target)
        return transform.after if transform is not None else group.bbox

    def _add_boxes(self) -> None:
        for element in list(self.effective.added.values()):
            if element.kind == "modifier_box":
                self._add_explicit_box(element)
        for op in self.effective.auto_boxes:
            self._add_dynamic_boxes(op)

    def _parent_group(
        self, element_or_target: str | None, uid: str
    ) -> SlotGroup | None:
        if element_or_target is None:
            return None
        key, dup = parse_target(element_or_target)
        group = self.scene.primary_for_input(key, dup)
        if group is None or group.bbox is None:
            self._skip([uid], "parent_missing", element_or_target)
            return None
        return group

    def _add_explicit_box(self, element: AddedElement) -> None:
        group = self._parent_group(element.parent, element.source_uid)
        if group is None or element.state.hidden:
            return
        base = self._current_bbox(group)
        assert base is not None
        width = element.width if element.width else base.width * 0.85
        height = element.height if element.height else base.height * 0.85
        rect = Rect(
            base.x + element.dx + element.state.dx,
            base.y + element.dy + element.state.dy,
            width,
            height,
        )
        self._create_box(
            group, _BoxSpec(element.uid, element.index or 1, element.content, rect)
        )

    def _add_dynamic_boxes(self, op: AddModifierBoxesOp) -> None:
        group = self._parent_group(op.target, op.uid)
        if group is None or group.input_key is None:
            return
        wanted = (
            self.job.resolver.modifier_count(group.input_key)
            if op.count == "auto"
            else int(op.count)
        )
        if wanted <= 0:
            return
        extra = self.added_rects + [t.after for t in self.transforms.values()]
        planned = plan_auto_add(
            self.scene,
            {group.target: wanted},
            PlanOptions(op.arrangement, op.gap, op.scale, op.max_count),
            extra_occupied=extra,
            parent_rects={group.target: self._current_bbox(group) or group.bbox},
        )
        for box in planned.placed:
            self._create_box(
                group, _BoxSpec(op.box_uid(box.index), box.index, op.content, box.rect)
            )
        if planned.unplaced:
            self.result.unplaced.extend(planned.unplaced)
            self._notice(
                "box_unplaced", group.target, op.uid, f"{len(planned.unplaced)} box(es)"
            )
            if RenderNotice.BOXES_UNPLACED not in self.job.notices:
                self.job.notices.append(RenderNotice.BOXES_UNPLACED)

    def _create_box(self, group: SlotGroup, spec: _BoxSpec) -> None:
        parent_slot = next(
            (s for s in group.slots if s.label_group is not None), group.slots[0]
        )
        assert group.bbox is not None and group.input_key is not None
        suffix = ROLE_FOR_CONTENT[spec.content]
        spec.token = f"{group.input_key.upper()}_MODIFIER_{spec.index}{suffix}"
        ratio = 1.0
        if group.bbox.height:
            ratio = min(1.0, max(0.6, spec.rect.height / group.bbox.height))
        font_size = max(
            MIN_FONT_SIZE, round(label_font_size(parent_slot.label_group) * ratio, 1)
        )
        shape, label = clone_box(parent_slot, spec.rect, spec.token, font_size)
        anchor = self._dom_anchor.get(group.target)
        if anchor is None:
            anchor = _top_node(slot_nodes(parent_slot)[-1])
        anchor.addnext(shape)
        shape.addnext(label)
        self._dom_anchor[group.target] = label
        cell = self._box_cell(
            parent_slot, spec, font_size, self._cell_anchor.get(group.target)
        )
        self._cell_anchor[group.target] = cell
        self._register_added(group, spec, shape, label, cell)

    def _box_cell(
        self, parent_slot: Slot, spec: _BoxSpec, font_size: float, after=None
    ):
        ox, oy = self.scene.offset
        parent_cell = parent_slot.cell
        style: dict[str, str | None] = {
            "rounded": "1",
            "whiteSpace": "wrap",
            "html": "1",
        }
        parent_id = "1"
        origin = (0.0, 0.0)
        if parent_cell is not None:
            style = parent_cell.style_dict
            style.pop("rotation", None)
            parent_id = parent_cell.parent or "1"
            origin = cell_origin(parent_cell, self.scene.cells)
        style["fontSize"] = f"{font_size:g}"
        geometry = Rect(
            spec.rect.x - ox - origin[0],
            spec.rect.y - oy - origin[1],
            spec.rect.width,
            spec.rect.height,
        )
        cell = NewCell(
            f"{ADDED_CELL_PREFIX}{spec.uid}", spec.token, style, geometry, parent_id
        )
        return add_model_cell(
            self.model, cell, after if after is not None else parent_cell
        )

    def _register_added(
        self, group: SlotGroup, spec: _BoxSpec, shape: Any, label: Any, cell
    ) -> None:
        info = classify(spec.token)
        targets = [
            TextTarget(div, TextTargetKind.FOREIGN_OBJECT)
            for div in [inner_div(label)]
            if div is not None
        ]
        text = text_element(label)
        if text is not None:
            targets.append(TextTarget(text, TextTargetKind.TEXT))
        slot = Slot(
            key=info.token,
            role=info.role,
            input_key=info.input_key,
            modifier_index=info.modifier_index,
            tokens=(info.token,),
            label_group=label,
            text_targets=targets,
            cell=cell,
            shape=ShapeRef(shape, spec.rect),
            bbox=spec.rect,
        )
        self.slot_map.slots.append(slot)
        self.added_rects.append(spec.rect)
        self.result.added_count += 1
        self.annotations.append(
            (
                shape,
                {
                    "data-jd-slot": spec.uid,
                    "data-jd-added": spec.uid,
                    "data-jd-role": info.role.value,
                },
            )
        )
        self.annotations.append(
            (
                label,
                {
                    "data-jd-slot": spec.uid,
                    "data-jd-added": spec.uid,
                    "data-jd-role": info.role.value,
                },
            )
        )
        self.added_info.append(
            LayoutSlotInfo(
                target=spec.uid,
                key=info.token,
                role=info.role.value,
                input_key=info.input_key,
                modifier_index=info.modifier_index,
                original_bbox=spec.rect,
                bbox=spec.rect,
                dx=0.0,
                dy=0.0,
                hidden=False,
                movable=True,
                resizable=True,
                rotated=False,
                stacked=1,
                edges=(),
                layer=self.layers.layer_of(spec.uid.split(":")[0]),
                added_uid=spec.uid,
                parent=group.target,
            )
        )

    # ── Notes ──

    def _main_container(self) -> Any:
        for child in self.doc.root:
            if localname(child) == "g":
                return child
        return self.doc.root

    def _add_notes(self) -> None:
        for element in self.effective.added.values():
            if element.kind == "note" and not element.state.hidden:
                self._add_note(element)

    def _add_note(self, element: AddedElement) -> None:
        base = Rect(0.0, 0.0, 0.0, 0.0)
        if element.parent is not None:
            group = self._parent_group(element.parent, element.uid)
            if group is None:
                return
            base = self._current_bbox(group) or base
        rect = Rect(
            base.x + element.dx + element.state.dx,
            base.y + element.dy + element.state.dy,
            element.width or 120.0,
            element.height or 24.0,
        )
        style = element.style or NoteStyle()
        text = element.text.replace("PROFILE_NAME", "TEMPLATE_NAME")
        shape, label = build_note(rect, text, style)
        container = self._main_container()
        if shape is not None:
            container.append(shape)
            self.annotations.append(
                (
                    shape,
                    {
                        "data-jd-slot": element.uid,
                        "data-jd-added": element.uid,
                        "data-jd-role": "note",
                    },
                )
            )
        container.append(label)
        self.annotations.append(
            (
                label,
                {
                    "data-jd-slot": element.uid,
                    "data-jd-added": element.uid,
                    "data-jd-role": "note",
                },
            )
        )
        self._note_cell(element, rect, text, style)
        self.added_rects.append(rect)
        self.result.added_count += 1
        self.added_info.append(
            LayoutSlotInfo(
                target=element.uid,
                key="note",
                role="note",
                input_key=None,
                modifier_index=None,
                original_bbox=rect,
                bbox=rect,
                dx=0.0,
                dy=0.0,
                hidden=False,
                movable=True,
                resizable=True,
                rotated=False,
                stacked=1,
                edges=(),
                layer=self.layers.layer_of(element.uid),
                added_uid=element.uid,
                parent=element.parent,
                text=element.text,
            )
        )

    def _note_cell(self, element: AddedElement, rect: Rect, text: str, style) -> None:
        ox, oy = self.scene.offset
        cell_style: dict[str, str | None] = {
            "text": None,
            "html": "1",
            "whiteSpace": "wrap",
            "align": style.align,
            "verticalAlign": "middle",
            "fontSize": f"{style.font_size:g}",
            "fontFamily": style.font_family,
            "fontColor": style.colour,
            "fillColor": style.fill or "none",
            "strokeColor": style.stroke or "none",
            "jdNote": "1",
        }
        if style.bold:
            cell_style["fontStyle"] = "1"
        geometry = Rect(rect.x - ox, rect.y - oy, rect.width, rect.height)
        cell = NewCell(
            f"{ADDED_CELL_PREFIX}{element.uid}",
            html.escape(text, quote=False),
            cell_style,
            geometry,
        )
        add_model_cell(self.model, cell)

    # ── Annotations and description ──

    def _annotate(self) -> None:
        for group in self.scene.groups:
            attributes = {
                "data-jd-slot": group.target,
                "data-jd-role": group.role.value,
            }
            for slot in group.slots:
                for node in self._annotatable_nodes(slot):
                    _set_attributes(node, attributes)
        for element, attributes in self.annotations:
            _set_attributes(element, attributes)
        self._annotate_edges()

    def _annotate_edges(self) -> None:
        for attachment in self.scene.attachments:
            edge_id = attachment.edge_id
            if edge_id is None:
                continue
            if attachment.edge.element is not None:
                attachment.edge.element.set("data-jd-edge", edge_id)
            for marker in _edge_markers(attachment):
                marker.set("data-jd-edge", edge_id)

    @staticmethod
    def _annotatable_nodes(slot: Slot) -> list[Any]:
        nodes = []
        if slot.shape is not None:
            nodes.append(slot.shape.element)
        if slot.label_group is not None:
            nodes.append(slot.label_group)
            top = _top_node(slot.label_group)
            if top is not slot.label_group and top.get("data-jd-op") is not None:
                nodes.append(top)
        return nodes

    def _edges_of(self, target: str) -> tuple[str, ...]:
        return tuple(
            a.edge_id
            for a in self.scene.attachments
            if a.edge_id is not None and target in a.attached_groups()
        )

    def _layer_of_state(self, state: SlotState | None) -> str | None:
        if state is None or not state.op_uids:
            return None
        return self.layers.layer_of(state.op_uids[-1])

    def _describe(self) -> None:
        supported = self.result.supported
        for group in self.scene.groups:
            state = self.effective.slots.get(group.target)
            transform = self.transforms.get(group.target)
            self.result.slots.append(
                LayoutSlotInfo(
                    target=group.target,
                    key=group.key,
                    role=group.role.value,
                    input_key=group.input_key,
                    modifier_index=group.modifier_index,
                    original_bbox=group.bbox,
                    bbox=transform.after if transform else group.bbox,
                    dx=transform.delta[0] if transform else 0.0,
                    dy=transform.delta[1] if transform else 0.0,
                    hidden=group.target in self.hidden,
                    movable=supported and group.movable,
                    resizable=supported and group.resizable,
                    rotated=group.rotated,
                    stacked=len(group.slots),
                    edges=self._edges_of(group.target),
                    layer=self._layer_of_state(state),
                )
            )
        self.result.slots.extend(self.added_info)
        for attachment in self.scene.attachments:
            edge_id = attachment.edge_id
            if edge_id is None:
                continue
            self.result.edges.append(
                LayoutEdgeInfo(
                    edge_id=edge_id,
                    points=tuple(edge_points(attachment.edge)),
                    source_slot=attachment.source.group,
                    source_kind=attachment.source.kind,
                    target_slot=attachment.target.group,
                    target_kind=attachment.target.kind,
                    hidden=edge_id in self.hidden_edges,
                    rendered=attachment.edge.element is not None,
                )
            )

    def _check_drift(self) -> None:
        current = self.job.content_hash
        if current is None:
            return
        for document in (self.layers.template, self.layers.profile):
            if document.ops and document.content_hash not in (None, current):
                self._notice("template_updated", detail=document.profile_key)
                if RenderNotice.TEMPLATE_UPDATED not in self.job.notices:
                    self.job.notices.append(RenderNotice.TEMPLATE_UPDATED)
                return


# ── Hook ──


def resolve_layers(job: RenderJob) -> LayoutLayers:
    if job.layers is not None:
        return job.layers
    return job.ctx.layers_for(job.template_key, job.device_guid, job.profile_key)


def apply_layout(job: RenderJob) -> None:
    """Layout hook: apply the job's layers (and annotate when ``ctx.preview``)."""
    from joystick_diagrams.render.pipeline import record_overflow

    layers = resolve_layers(job)
    if layers.is_empty and not job.ctx.preview and not job.describe_layout:
        return
    if job.slots is None:
        return
    applier = LayoutApplier(job, layers)
    job.layout = applier.run()
    job.skipped_ops.extend(job.layout.skipped_ops)
    record_overflow(job)
    for slot in job.doc.root.iter(f"{SVG}g"):  # keep lxml from emitting empty tails
        if slot.get("data-jd-op") is not None and slot.tail == "":
            slot.tail = None


__all__ = [
    "LayoutApplier",
    "LayoutEdgeInfo",
    "LayoutNotice",
    "LayoutResult",
    "LayoutSlotInfo",
    "apply_layout",
    "resolve_layers",
]

if __name__ == "__main__":
    pass
