"""Layout op model: what a user changed on a diagram, independent of any device.

This module is pure data (pydantic v2) plus the effective-state fold. Applying
ops to a rendered SVG lives in ``render/layout_apply.py``; persistence in
``db/layout_service.py``; automatic placement of modifier boxes in
``render/auto_layout.py``.

Targets
-------
Every op points at a *stable slot identity* so it survives template updates:

- ``"button_1"`` / ``"button_1#2"``: the placeholder key (lower-cased, ``#1``
  implied) plus the duplicate index when the template shows the same key in
  several places (``KEY#n``, counted top-to-bottom, left-to-right). Stacked
  duplicates (same key, bboxes overlapping > 80 %) form **one** identity and
  move together. ``parse_target`` / ``format_target`` normalise the string.
- ``"<uid>"`` of an added element (a modifier box or a note): added elements
  get a uuid4 hex uid when they are created and later ops (move, hide, remove)
  target that uid.
- ``MoveEdgeEndOp`` targets a leader line by its draw.io cell id.

Geometry is stored **relative to the parent slot's original bbox** (its
rendered position before any op): a ``MoveOp`` is a delta, an added box is
``(dx, dy, width, height)`` from the parent's top-left corner, a note is either
page-absolute or relative to an ``anchor`` slot. Relative storage is what lets
ops still fit after a template author nudges the whole diagram.

JSON shape (``LayoutDocument.model_dump_json()``)::

    {
        "schema_version": 1,
        "template_key": "bundled:Starter Template.svg",
        "profile_key": "",
        "content_hash": "…",
        "ops": [
            {"op": "move", "uid": "…", "target": "button_1", "dx": 12.5, "dy": -3},
            {
                "op": "resize",
                "uid": "…",
                "target": "button_1",
                "width": 140,
                "height": 30,
            },
            {"op": "hide", "uid": "…", "target": "button_2", "hide_leaders": true},
            {"op": "show", "uid": "…", "target": "button_2"},
            {
                "op": "add_modifier_boxes",
                "uid": "…",
                "target": "button_1",
                "count": "auto",
                "max_count": 4,
                "arrangement": "below",
                "gap": 5,
                "scale": 0.85,
                "boxes": null,
            },
            {
                "op": "add_modifier_boxes",
                "uid": "…",
                "target": "button_3",
                "count": 2,
                "boxes": [
                    {
                        "index": 1,
                        "uid": "…",
                        "dx": 0,
                        "dy": 34,
                        "width": 120,
                        "height": 26,
                    },
                    {
                        "index": 2,
                        "uid": "…",
                        "dx": 0,
                        "dy": 64,
                        "width": 120,
                        "height": 26,
                    },
                ],
            },
            {
                "op": "add_modifier_box",
                "uid": "…",
                "target": "button_1",
                "index": 1,
                "dx": 0,
                "dy": 34,
                "width": 120,
                "height": 26,
                "content": "full",
            },
            {"op": "remove_added", "uid": "…", "target": "<uid of the added element>"},
            {
                "op": "add_note",
                "uid": "…",
                "text": "PROFILE_NAME · CURRENT_DATE",
                "x": 20,
                "y": 20,
                "width": 200,
                "height": 24,
                "anchor": null,
                "style": {
                    "font_size": 12,
                    "colour": "#000000",
                    "fill": "#FFFFFF",
                    "stroke": "#000000",
                    "bold": false,
                    "align": "center",
                },
            },
            {
                "op": "move_edge_end",
                "uid": "…",
                "edge": "<cell id>",
                "end": "target",
                "dx": 10,
                "dy": 0,
            },
            {"op": "reset", "uid": "…", "target": "button_1"},
        ],
    }

Layers and folding
------------------
``LayoutLayers(template, profile)`` holds the two stored documents for one
diagram: the template layer (``profile_key == ""``, "all profiles on this
diagram") and the profile layer. ``fold_ops(layers.all_ops())`` replays the
ordered list (template first, then profile) into an ``EffectiveLayout``: per
target the summed delta, the last size, the hidden flag; the added elements in
creation order (each with its own state); the dynamic ``add_modifier_boxes``
requests; and the leader-line end deltas. The fold is what the editor shows
and what ``layout_apply`` renders. Ops are undo-friendly: the editor keeps an
ordered list and removes or replaces entries (``remove_op`` / ``replace_op`` on
``LayoutDocument``), re-folding each time.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = 1
TEMPLATE_LAYER = ""  # profile_key of the "all profiles on this diagram" layer
STACKED_OVERLAP_RATIO = 0.8
DEFAULT_MAX_BOXES = 4
DEFAULT_BOX_GAP = 5.0
DEFAULT_BOX_SCALE = 0.85

Arrangement = Literal["auto", "below", "right", "left", "above"]
EdgeEnd = Literal["source", "target"]
BoxContent = Literal["full", "key", "action"]


def new_uid() -> str:
    return uuid.uuid4().hex


# ── Targets ──


def parse_target(target: str) -> tuple[str, int]:
    """``"BUTTON_1#2"`` → ``("button_1", 2)``; ``"button_1"`` → ``("button_1", 1)``."""
    text = target.strip()
    key, sep, dup = text.rpartition("#")
    if sep and dup.isdigit() and key:
        return key.lower(), max(int(dup), 1)
    return text.lower(), 1


def format_target(key: str, dup: int = 1) -> str:
    return f"{key.lower()}#{dup}"


def normalise_target(target: str) -> str:
    key, dup = parse_target(target)
    return format_target(key, dup)


# ── Ops ──


class _Op(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    uid: str = Field(default_factory=new_uid, min_length=1)


class _SlotOp(_Op):
    target: str = Field(min_length=1)

    @field_validator("target")
    @classmethod
    def _normalise(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("target must not be blank")
        # Added-element uids (32 hex chars) are kept verbatim; slot keys are normalised.
        return value if _looks_like_uid(value) else normalise_target(value)


def _looks_like_uid(value: str) -> bool:
    return len(value) == 32 and all(c in "0123456789abcdef" for c in value.lower())


class MoveOp(_SlotOp):
    """Translate a slot (or an added element) by a delta from its original place."""

    op: Literal["move"] = "move"
    dx: float = 0.0
    dy: float = 0.0


class ResizeOp(_SlotOp):
    """Set a slot's size (top-left anchored). Only ``<rect>``, unrotated slots resize."""

    op: Literal["resize"] = "resize"
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class HideOp(_SlotOp):
    op: Literal["hide"] = "hide"
    hide_leaders: bool = True


class ShowOp(_SlotOp):
    op: Literal["show"] = "show"


class BoxGeometry(BaseModel):
    """One added modifier box, relative to the parent slot's original top-left."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1)  # the N of KEY_MODIFIER_N
    uid: str = Field(default_factory=new_uid, min_length=1)
    dx: float
    dy: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class AddModifierBoxesOp(_SlotOp):
    """Modifier boxes for one input (``target`` is the input key, e.g. ``button_1``).

    With ``boxes`` set the geometry is explicit (what auto-add and the editor
    store). Without it the op is *dynamic*: boxes are laid out at render time
    around the parent (``count="auto"`` → one per bound modifier, up to
    ``max_count``), so the result follows the profile's actual modifiers.
    """

    op: Literal["add_modifier_boxes"] = "add_modifier_boxes"
    count: int | Literal["auto"] = "auto"
    max_count: int = Field(default=DEFAULT_MAX_BOXES, ge=1)
    arrangement: Arrangement = "auto"
    gap: float = Field(default=DEFAULT_BOX_GAP, ge=0)
    scale: float = Field(default=DEFAULT_BOX_SCALE, gt=0, le=2)
    boxes: list[BoxGeometry] | None = None
    content: BoxContent = "full"

    @field_validator("count")
    @classmethod
    def _positive(cls, value):
        if isinstance(value, int) and value < 1:
            raise ValueError("count must be at least 1")
        return value

    def box_uid(self, index: int) -> str:
        """Stable uid of the box with ``index`` (explicit uid, else derived)."""
        for box in self.boxes or ():
            if box.index == index:
                return box.uid
        return f"{self.uid}:{index}"


class AddModifierBoxOp(_SlotOp):
    """A single manually placed modifier box for ``target`` (the input key)."""

    op: Literal["add_modifier_box"] = "add_modifier_box"
    index: int = Field(ge=1)
    dx: float
    dy: float
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    content: BoxContent = "full"


class RemoveAddedElementOp(_SlotOp):
    """Remove an added box or note; ``target`` is the element's uid."""

    op: Literal["remove_added"] = "remove_added"


class NoteStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    font_size: float = Field(default=12, gt=0)
    font_family: str = "Helvetica"
    colour: str = "#000000"
    fill: str | None = "#FFFFFF"
    stroke: str | None = "#000000"
    bold: bool = False
    align: Literal["left", "center", "right"] = "center"


class AddNoteOp(_Op):
    """A free text box. ``text`` may contain ``TEMPLATE_NAME``/``PROFILE_NAME``
    (both resolve to the profile name, as ``TEMPLATE_NAME`` does on every
    template) and ``CURRENT_DATE``; the fill stage resolves them."""

    op: Literal["add_note"] = "add_note"
    text: str = ""
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    anchor: str | None = None  # slot target; x/y are then relative to its bbox
    style: NoteStyle = Field(default_factory=NoteStyle)

    @field_validator("anchor")
    @classmethod
    def _normalise_anchor(cls, value: str | None) -> str | None:
        return normalise_target(value) if value else None


class EditNoteOp(_SlotOp):
    """Change the text (and optionally style) of a note; ``target`` is its uid."""

    op: Literal["edit_note"] = "edit_note"
    text: str
    style: NoteStyle | None = None


class MoveEdgeEndOp(_Op):
    """Drag the free end of a leader line (``edge`` is the draw.io cell id)."""

    op: Literal["move_edge_end"] = "move_edge_end"
    edge: str = Field(min_length=1)
    end: EdgeEnd
    dx: float = 0.0
    dy: float = 0.0


class ResetSlotOp(_SlotOp):
    """Cancel every earlier op on ``target`` (and the boxes added to it)."""

    op: Literal["reset"] = "reset"


LayoutOp = Annotated[
    Union[
        MoveOp,
        ResizeOp,
        HideOp,
        ShowOp,
        AddModifierBoxesOp,
        AddModifierBoxOp,
        RemoveAddedElementOp,
        AddNoteOp,
        EditNoteOp,
        MoveEdgeEndOp,
        ResetSlotOp,
    ],
    Field(discriminator="op"),
]


class _OpList(BaseModel):
    ops: list[LayoutOp]


def parse_op(data: dict | str) -> LayoutOp:
    """Validate one op from a dict or JSON string (raises ``pydantic.ValidationError``)."""
    if isinstance(data, str):
        return _OpList.model_validate_json(f'{{"ops": [{data}]}}').ops[0]
    return _OpList.model_validate({"ops": [data]}).ops[0]


# ── Documents and layers ──


class LayoutDocument(BaseModel):
    """The ordered op list stored for one (template, layer)."""

    model_config = ConfigDict(extra="ignore")

    schema_version: int = SCHEMA_VERSION
    template_key: str | None = None
    device_guid: str = ""  # controller the ops belong to; "" = every controller
    profile_key: str = TEMPLATE_LAYER
    content_hash: str | None = None  # of the template the ops were made on
    ops: list[LayoutOp] = Field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.ops

    def find(self, uid: str) -> LayoutOp | None:
        return next((op for op in self.ops if op.uid == uid), None)

    def append(self, op: LayoutOp) -> LayoutOp:
        self.ops.append(op)
        return op

    def remove_op(self, uid: str) -> bool:
        before = len(self.ops)
        self.ops = [op for op in self.ops if op.uid != uid]
        return len(self.ops) != before

    def replace_op(self, uid: str, op: LayoutOp) -> bool:
        for index, existing in enumerate(self.ops):
            if existing.uid == uid:
                self.ops[index] = op
                return True
        return False

    def coalesce_move(self, op: MoveOp) -> MoveOp:
        """Append a move, merging into a trailing move of the same target (nudges)."""
        last = self.ops[-1] if self.ops else None
        if isinstance(last, MoveOp) and last.target == op.target:
            merged = last.model_copy(
                update={"dx": last.dx + op.dx, "dy": last.dy + op.dy}
            )
            self.ops[-1] = merged
            return merged
        self.ops.append(op)
        return op


@dataclass(frozen=True)
class LayoutLayers:
    """Template layer then profile layer for one diagram (either may be empty)."""

    template: LayoutDocument = field(default_factory=LayoutDocument)
    profile: LayoutDocument = field(default_factory=LayoutDocument)

    def all_ops(self) -> list[LayoutOp]:
        return list(self.template.ops) + list(self.profile.ops)

    @property
    def is_empty(self) -> bool:
        return self.template.is_empty and self.profile.is_empty

    def layer_of(self, uid: str) -> Literal["template", "profile"] | None:
        if self.profile.find(uid) is not None:
            return "profile"
        if self.template.find(uid) is not None:
            return "template"
        return None


# ── Effective state ──


@dataclass
class SlotState:
    dx: float = 0.0
    dy: float = 0.0
    size: tuple[float, float] | None = None  # (width, height) after the last resize
    hidden: bool = False
    hide_leaders: bool = True
    op_uids: list[str] = field(default_factory=list)  # every op that touched it

    @property
    def is_default(self) -> bool:
        return not (self.dx or self.dy or self.size or self.hidden)


@dataclass
class AddedElement:
    """A modifier box or note created by an op, plus its own later edits."""

    uid: str
    kind: Literal["modifier_box", "note"]
    source_uid: str  # the op that created it
    parent: (
        str | None
    )  # slot target the geometry is relative to (box parent / note anchor)
    index: int | None  # modifier index for boxes
    dx: float
    dy: float
    width: float | None
    height: float | None
    text: str = ""
    style: NoteStyle | None = None
    content: BoxContent = "full"
    state: SlotState = field(default_factory=SlotState)


@dataclass
class EffectiveLayout:
    slots: dict[str, SlotState] = field(default_factory=dict)
    added: dict[str, AddedElement] = field(default_factory=dict)  # insertion ordered
    auto_boxes: list[AddModifierBoxesOp] = field(default_factory=list)  # dynamic ones
    edge_ends: dict[tuple[str, str], tuple[float, float]] = field(default_factory=dict)

    def state_for(self, target: str) -> SlotState:
        if target in self.added:
            return self.added[target].state
        return self.slots.setdefault(target, SlotState())

    def changed_slots(self) -> dict[str, SlotState]:
        return {k: v for k, v in self.slots.items() if not v.is_default}

    @property
    def is_empty(self) -> bool:
        return not (
            self.changed_slots() or self.added or self.auto_boxes or self.edge_ends
        )


def _fold_boxes(effective: EffectiveLayout, op: AddModifierBoxesOp) -> None:
    if op.boxes is None:
        effective.auto_boxes = [
            a for a in effective.auto_boxes if a.target != op.target
        ]
        effective.auto_boxes.append(op)
        return
    for box in op.boxes:
        effective.added[box.uid] = AddedElement(
            uid=box.uid,
            kind="modifier_box",
            source_uid=op.uid,
            parent=op.target,
            index=box.index,
            dx=box.dx,
            dy=box.dy,
            width=box.width,
            height=box.height,
            content=op.content,
        )


def _fold_reset(effective: EffectiveLayout, target: str) -> None:
    effective.slots.pop(target, None)
    if target in effective.added:
        effective.added[target].state = SlotState()
        return
    effective.added = {
        uid: element
        for uid, element in effective.added.items()
        if element.parent != target
    }
    effective.auto_boxes = [a for a in effective.auto_boxes if a.target != target]


def _fold_move(effective: EffectiveLayout, op: MoveOp) -> None:
    state = effective.state_for(op.target)
    state.dx += op.dx
    state.dy += op.dy
    state.op_uids.append(op.uid)


def _fold_resize(effective: EffectiveLayout, op: ResizeOp) -> None:
    state = effective.state_for(op.target)
    state.size = (op.width, op.height)
    state.op_uids.append(op.uid)


def _fold_hide(effective: EffectiveLayout, op: HideOp) -> None:
    state = effective.state_for(op.target)
    state.hidden = True
    state.hide_leaders = op.hide_leaders
    state.op_uids.append(op.uid)


def _fold_show(effective: EffectiveLayout, op: ShowOp) -> None:
    state = effective.state_for(op.target)
    state.hidden = False
    state.op_uids.append(op.uid)


def _fold_box(effective: EffectiveLayout, op: AddModifierBoxOp) -> None:
    effective.added[op.uid] = AddedElement(
        uid=op.uid,
        kind="modifier_box",
        source_uid=op.uid,
        parent=op.target,
        index=op.index,
        dx=op.dx,
        dy=op.dy,
        width=op.width,
        height=op.height,
        content=op.content,
    )


def _fold_note(effective: EffectiveLayout, op: AddNoteOp) -> None:
    effective.added[op.uid] = AddedElement(
        uid=op.uid,
        kind="note",
        source_uid=op.uid,
        parent=op.anchor,
        index=None,
        dx=op.x,
        dy=op.y,
        width=op.width,
        height=op.height,
        text=op.text,
        style=op.style,
    )


def _fold_edit_note(effective: EffectiveLayout, op: EditNoteOp) -> None:
    note = effective.added.get(op.target)
    if note is not None and note.kind == "note":
        note.text = op.text
        if op.style is not None:
            note.style = op.style


def _fold_remove(effective: EffectiveLayout, op: RemoveAddedElementOp) -> None:
    effective.added.pop(op.target, None)


def _fold_edge_end(effective: EffectiveLayout, op: MoveEdgeEndOp) -> None:
    key = (op.edge, op.end)
    dx, dy = effective.edge_ends.get(key, (0.0, 0.0))
    effective.edge_ends[key] = (dx + op.dx, dy + op.dy)


_FOLDERS = {
    MoveOp: _fold_move,
    ResizeOp: _fold_resize,
    HideOp: _fold_hide,
    ShowOp: _fold_show,
    AddModifierBoxesOp: _fold_boxes,
    AddModifierBoxOp: _fold_box,
    AddNoteOp: _fold_note,
    EditNoteOp: _fold_edit_note,
    RemoveAddedElementOp: _fold_remove,
    MoveEdgeEndOp: _fold_edge_end,
    ResetSlotOp: lambda effective, op: _fold_reset(effective, op.target),
}


def fold_ops(ops: Iterable[LayoutOp]) -> EffectiveLayout:
    """Replay an ordered op list into the effective per-target state."""
    effective = EffectiveLayout()
    for op in ops:
        _FOLDERS[type(op)](effective, op)
    return effective


__all__ = [
    "DEFAULT_BOX_GAP",
    "DEFAULT_BOX_SCALE",
    "DEFAULT_MAX_BOXES",
    "SCHEMA_VERSION",
    "STACKED_OVERLAP_RATIO",
    "TEMPLATE_LAYER",
    "AddModifierBoxOp",
    "AddModifierBoxesOp",
    "AddNoteOp",
    "AddedElement",
    "Arrangement",
    "BoxGeometry",
    "EditNoteOp",
    "EffectiveLayout",
    "HideOp",
    "LayoutDocument",
    "LayoutLayers",
    "LayoutOp",
    "MoveEdgeEndOp",
    "MoveOp",
    "NoteStyle",
    "RemoveAddedElementOp",
    "ResetSlotOp",
    "ResizeOp",
    "ShowOp",
    "SlotState",
    "fold_ops",
    "format_target",
    "new_uid",
    "normalise_target",
    "parse_op",
    "parse_target",
]

if __name__ == "__main__":
    pass
