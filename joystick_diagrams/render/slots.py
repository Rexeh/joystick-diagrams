"""Slot model shared by the DOM render engine and later styling/layout work.

A *slot* is one rendered label in a draw.io SVG that carries at least one
placeholder token (``BUTTON_1``, ``AXIS_X_MODIFIER_1_KEY``, ``TEMPLATE_NAME`` …)
together with everything the renderer could determine about it:

- the rendered text nodes that must be filled (``TextTarget``: the innermost
  ``<div>`` inside the ``<foreignObject>`` and the ``<text>`` fallback),
- the matching draw.io model cell (``MxCell``) when alignment succeeded,
- the shape element drawn behind the label (``ShapeRef``) and its bbox,
- the edges attached to the cell where determinable (``EdgeRef``).

Later milestones (theme writer, modifier colouring, layout ops) consume this
model through ``SlotMap``; they must never re-derive structure from the raw SVG.

Roles
-----
``SlotRole`` is the *structural* role of the primary token of a slot. It is
distinct from the styling roles a theme will define (``ThemeRole`` in a later
milestone).

Multi-token labels
------------------
A rendered label may hold several tokens (``BUTTON_62<br>BUTTON_35``). One
``Slot`` is produced per rendered label; ``Slot.tokens`` lists every token
(lower-cased) and ``Slot.key``/``Slot.role`` describe the first one.
``SlotMap.by_token`` maps every token to the slots that carry it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from joystick_diagrams.render.drawio_model import MxCell

SVG_NS = "http://www.w3.org/2000/svg"


class SlotRole(str, Enum):
    """Structural role of a placeholder token."""

    ACTION = "action"  # BUTTON_1 / AXIS_X / POV_1_U – the primary binding
    MODIFIERS = "modifiers"  # BUTTON_1_MODIFIERS – all modifiers joined
    MODIFIER = "modifier"  # BUTTON_1_MODIFIER_2 – "command - key"
    MODIFIER_KEY = "modifier_key"  # BUTTON_1_MODIFIER_2_KEY
    MODIFIER_ACTION = "modifier_action"  # BUTTON_1_MODIFIER_2_ACTION
    TITLE = "title"  # TEMPLATE_NAME
    DATE = "date"  # CURRENT_DATE
    UNKNOWN = "unknown"  # legacy-only token shapes (POV_1_LL, *_MODIFIER_1_STYLE)


class Capability(str, Enum):
    """What an adapter could determine for a document (see adapters/base.py)."""

    TEXT = "text"  # text replacement in rendered nodes
    TEXT_STYLE = "text_style"  # CSS/attribute styling of the text targets
    SHAPE_STYLE = "shape_style"  # shape element and model cell are known
    EDGES = "edges"  # attached edges are known
    LAYOUT = "layout"  # geometry is validated, slots can be moved


class TextTargetKind(str, Enum):
    FOREIGN_OBJECT = "foreign_object"  # innermost xhtml <div> under <foreignObject>
    TEXT = "text"  # the <text> fallback inside <switch>


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def centre(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    def translated(self, dx: float, dy: float) -> Rect:
        return Rect(self.x + dx, self.y + dy, self.width, self.height)

    def expanded(self, margin: float) -> Rect:
        return Rect(
            self.x - margin,
            self.y - margin,
            self.width + 2 * margin,
            self.height + 2 * margin,
        )

    def intersects(self, other: Rect, tolerance: float = 0.0) -> bool:
        """Whether the interiors overlap (touching edges within ``tolerance`` don't)."""
        return (
            self.x < other.right - tolerance
            and other.x < self.right - tolerance
            and self.y < other.bottom - tolerance
            and other.y < self.bottom - tolerance
        )

    def contains(self, other: Rect, tolerance: float = 0.0) -> bool:
        return (
            other.x >= self.x - tolerance
            and other.y >= self.y - tolerance
            and other.right <= self.right + tolerance
            and other.bottom <= self.bottom + tolerance
        )

    def distance_to_point(self, x: float, y: float) -> float:
        """Euclidean distance from a point to the rectangle (0 when inside)."""
        dx = max(self.x - x, 0.0, x - self.right)
        dy = max(self.y - y, 0.0, y - self.bottom)
        return (dx * dx + dy * dy) ** 0.5

    def iou(self, other: Rect) -> float:
        """Intersection over union (1.0 for identical rectangles)."""
        w = min(self.right, other.right) - max(self.x, other.x)
        h = min(self.bottom, other.bottom) - max(self.y, other.y)
        if w <= 0 or h <= 0:
            return 0.0
        union = self.area + other.area - w * h
        return (w * h) / union if union > 0 else 0.0

    def overlap_ratio(self, other: Rect) -> float:
        """Intersection area over the smaller area (0 when disjoint)."""
        w = min(self.right, other.right) - max(self.x, other.x)
        h = min(self.bottom, other.bottom) - max(self.y, other.y)
        if w <= 0 or h <= 0:
            return 0.0
        smaller = min(self.area, other.area)
        return (w * h) / smaller if smaller > 0 else 0.0


@dataclass
class TextTarget:
    """A rendered element whose ``text``/``tail`` (and descendants) hold the label."""

    element: Any  # lxml element
    kind: TextTargetKind


@dataclass
class ShapeRef:
    """The shape drawn behind a label (``rect``/``ellipse``/``path``/``image``/``g``)."""

    element: Any  # lxml element
    bbox: Rect | None = None


@dataclass
class EdgeRef:
    """A model edge and, when known, how it is rendered.

    ``element`` is the themeable stroke element: the ``g[@data-cell-id]`` of the
    edge (cell-id files) or the bare stroke ``<path pointer-events="stroke">``
    (ordered files, matched by ``adapters/edge_mapping.py``); ``None`` when only
    the model knows the edge. ``markers`` are the arrowhead/oval elements drawn
    at the ends of a bare stroke path (empty for cell-id files, where they sit
    inside ``element``). ``edge_id`` is the model cell id, the stable identity
    layout ops (``MoveEdgeEndOp``) and ``data-jd-edge`` use.
    """

    cell: MxCell | None
    element: Any | None
    source_id: str | None
    target_id: str | None
    markers: tuple[Any, ...] = ()

    @property
    def edge_id(self) -> str | None:
        return self.cell.id if self.cell is not None else None

    @property
    def stroke_path(self) -> Any | None:
        """The rendered ``<path>`` carrying the line (searching inside a cell group)."""
        if self.element is None:
            return None
        if getattr(self.element, "tag", None) == f"{{{SVG_NS}}}path":
            return self.element
        for node in self.element.iter(f"{{{SVG_NS}}}path"):
            if node.get("pointer-events") == "stroke" or node.get("fill") == "none":
                return node
        return None


@dataclass
class Slot:
    key: str  # primary token, lower-cased, e.g. "button_1_modifier_1_key"
    role: SlotRole
    input_key: str | None  # "button_1" / "axis_x" / "pov_1_u" (lower-cased)
    modifier_index: int | None  # N for *_MODIFIER_N*
    tokens: tuple[str, ...]  # every token in this label, lower-cased
    label_group: Any | None = (
        None  # the <g transform="translate(...)"> holding <switch>
    )
    text_targets: list[TextTarget] = field(default_factory=list)
    cell: MxCell | None = None
    shape: ShapeRef | None = None
    bbox: Rect | None = None
    edges: list[EdgeRef] = field(default_factory=list)
    rotated: bool = False


@dataclass
class SlotMap:
    """All slots of a document plus what the adapter could guarantee about them."""

    adapter: str
    slots: list[Slot] = field(default_factory=list)
    capabilities: frozenset[Capability] = frozenset({Capability.TEXT})
    notices: list[str] = field(default_factory=list)
    offset: tuple[float, float] | None = None  # rendered minus model coordinates
    edges: list[EdgeRef] = field(
        default_factory=list
    )  # every model edge (attached or free), for layout

    @property
    def by_token(self) -> dict[str, list[Slot]]:
        index: dict[str, list[Slot]] = {}
        for slot in self.slots:
            for token in slot.tokens:
                index.setdefault(token, []).append(slot)
        return index

    def for_input(self, input_key: str) -> list[Slot]:
        wanted = input_key.lower()
        return [slot for slot in self.slots if slot.input_key == wanted]

    def modifier_box_count(self, input_key: str) -> int:
        """Number of distinct ``*_MODIFIER_N`` indexes the template offers for an input."""
        indexes = {
            slot.modifier_index
            for slot in self.for_input(input_key)
            if slot.modifier_index is not None
        }
        return len(indexes)


if __name__ == "__main__":
    pass
