"""Adapter for draw.io exports that tag every cell group with ``data-cell-id``.

Each rendered label sits inside ``<g data-cell-id="…">`` whose id is the model
cell id, so the mapping is exact: shape = the cell group's first shape group,
edges = the ``g[@data-cell-id]`` of every edge cell touching the slot's cell.
"""

from __future__ import annotations

from statistics import median
from typing import Any

from joystick_diagrams.render.adapters._common import (
    SVG,
    absolute_geometry,
    find_shape,
    geometry_matches,
    iter_label_groups,
    make_slot,
    offset_rect,
)
from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.drawio_model import DrawioModel, MxCell
from joystick_diagrams.render.slots import Capability, EdgeRef, Slot, SlotMap

FULL_CAPABILITIES = frozenset(Capability)


def cell_group_index(root: Any) -> dict[str, Any]:
    return {
        g.get("data-cell-id"): g
        for g in root.iter(f"{SVG}g")
        if g.get("data-cell-id") is not None
    }


def nearest_cell_group(element: Any) -> Any | None:
    for ancestor in element.iterancestors(f"{SVG}g"):
        if ancestor.get("data-cell-id") is not None:
            return ancestor
    return None


def derive_offset(
    slots: list[Slot], cells: dict[str, MxCell] | None = None
) -> tuple[float, float] | None:
    """Median (rendered - model) translation over slots with both a bbox and geometry.

    Geometry is taken in page coordinates (``absolute_geometry``) so cells nested
    in draw.io groups don't skew the median.
    """
    dxs: list[float] = []
    dys: list[float] = []
    for slot in slots:
        geometry = (
            absolute_geometry(slot.cell, cells) if slot.cell is not None else None
        )
        if slot.shape is None or slot.shape.bbox is None or geometry is None:
            continue
        dxs.append(slot.shape.bbox.x - geometry.x)
        dys.append(slot.shape.bbox.y - geometry.y)
    if not dxs:
        return None
    return (median(dxs), median(dys))


def attach_edges(
    slots: list[Slot],
    cells: dict[str, MxCell],
    elements: dict[str, Any],
    markers: dict[str, tuple[Any, ...]] | None = None,
) -> list[EdgeRef]:
    """Attach every edge cell to the slots whose cell it starts or ends at.

    Returns one ``EdgeRef`` per model edge (attached or free, in model order) so
    the ``SlotMap`` can list them all for layout work.
    """
    by_cell_id: dict[str, list[Slot]] = {}
    for slot in slots:
        if slot.cell is not None and slot.cell.id is not None:
            by_cell_id.setdefault(slot.cell.id, []).append(slot)
    edges: list[EdgeRef] = []
    for cell in cells.values():
        if not cell.is_edge:
            continue
        edge = EdgeRef(
            cell,
            elements.get(cell.id or ""),
            cell.source,
            cell.target,
            markers=(markers or {}).get(cell.id or "", ()),
        )
        edges.append(edge)
        for end in (cell.source, cell.target):
            for slot in by_cell_id.get(end or "", []):
                slot.edges.append(edge)
    return edges


def validate_geometry(
    slots: list[Slot], offset, cells: dict[str, MxCell] | None = None
) -> int:
    """Drop shapes that don't sit on their cell geometry; return the validated count.

    Without an offset nothing can be validated, so shapes are kept as found.
    Rotated cells are validated on the bbox of the rotated shape (``rect_of``
    applies ``rotate(...)`` transforms), so they keep their shapes too.
    """
    validated = 0
    if offset is None:
        return validated
    for slot in slots:
        if slot.cell is None:
            continue
        if geometry_matches(slot.shape, slot.cell, offset, cells):
            validated += 1
        elif not slot.rotated:
            slot.shape = None
            slot.bbox = offset_rect(absolute_geometry(slot.cell, cells), offset)
    return validated


class DrawioCellIdAdapter:
    name = "drawio_cell_id"

    def build_slots(self, doc: TemplateDocument, model: DrawioModel) -> SlotMap:
        cells = model.cells_by_id()
        groups = cell_group_index(doc.root)
        slots: list[Slot] = []
        for group in iter_label_groups(doc.root):
            if not group.tokens:
                continue
            cell_group = nearest_cell_group(group.container)
            cell = (
                cells.get(cell_group.get("data-cell-id"))
                if cell_group is not None
                else None
            )
            shape = find_shape(group.container, stop=cell_group)
            slots.append(make_slot(group, cell, shape))

        offset = derive_offset(slots, cells)
        validate_geometry(slots, offset, cells)
        edges = attach_edges(slots, cells, groups)
        slot_map = SlotMap(adapter=self.name, slots=slots, offset=offset, edges=edges)
        slot_map.capabilities = (
            FULL_CAPABILITIES
            if offset is not None
            else frozenset(
                {
                    Capability.TEXT,
                    Capability.TEXT_STYLE,
                    Capability.SHAPE_STYLE,
                    Capability.EDGES,
                }
            )
        )
        return slot_map


if __name__ == "__main__":
    pass
