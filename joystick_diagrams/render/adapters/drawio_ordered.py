"""Adapter for draw.io exports without ``data-cell-id`` (flat and grouped files).

draw.io renders cells in model order, so labelled vertex cells (visible, in
document order) and rendered label groups are aligned as two sequences, using
the normalised label text as the anchor. The constant per-file offset between
model and rendered coordinates is the median over matched pairs with a shape;
shapes that don't validate within ±3 px are dropped from their slot (the text
is still filled). Edges are attached from the model (``source``/``target``) and
their rendered stroke paths are found by ``edge_mapping.map_edges_to_paths``
(geometry-checked sequence alignment), so lines can be themed and followed.

If fewer than half of the token-bearing labels align, capabilities degrade to
TEXT and TEXT_STYLE (plan §1.5): text stays correct, nothing structural is touched.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from joystick_diagrams.render.adapters._common import (
    LabelGroup,
    find_shape,
    iter_label_groups,
    make_slot,
)
from joystick_diagrams.render.adapters.drawio_cell_id import (
    attach_edges,
    derive_offset,
    validate_geometry,
)
from joystick_diagrams.render.adapters.edge_mapping import map_edges_to_paths
from joystick_diagrams.render.adapters.text_only import TEXT_ONLY_CAPABILITIES
from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.drawio_model import DrawioModel, MxCell
from joystick_diagrams.render.slots import Capability, Slot, SlotMap

ALIGNMENT_THRESHOLD = 0.5
ALIGNED_CAPABILITIES = frozenset(
    {Capability.TEXT, Capability.TEXT_STYLE, Capability.SHAPE_STYLE, Capability.EDGES}
)


def is_visible(cell: MxCell, cells: dict[str, MxCell]) -> bool:
    """A cell is visible when neither it nor any ancestor layer is hidden."""
    current: MxCell | None = cell
    seen: set[str] = set()
    while current is not None:
        if not current.visible:
            return False
        parent_id = current.parent
        if parent_id is None or parent_id in seen:
            return True
        seen.add(parent_id)
        current = cells.get(parent_id)
    return True


def labelled_cells(model: DrawioModel) -> list[MxCell]:
    cells = model.cells_by_id()
    return [
        cell
        for cell in model.cells()
        if cell.is_vertex and cell.plain_label and is_visible(cell, cells)
    ]


def align(cells: list[MxCell], groups: list[LabelGroup]) -> dict[int, MxCell]:
    """Map rendered group index → model cell by longest common subsequence of labels."""
    left = [cell.plain_label.casefold() for cell in cells]
    right = [group.norm_text for group in groups]
    matcher = SequenceMatcher(None, left, right, autojunk=False)
    matched: dict[int, MxCell] = {}
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            matched[block.b + k] = cells[block.a + k]
    return matched


def _capabilities(slots: list[Slot], offset) -> frozenset[Capability]:
    if not slots:
        return TEXT_ONLY_CAPABILITIES
    aligned = sum(1 for slot in slots if slot.cell is not None)
    if aligned / len(slots) < ALIGNMENT_THRESHOLD:
        return TEXT_ONLY_CAPABILITIES
    if offset is None:
        return ALIGNED_CAPABILITIES
    return ALIGNED_CAPABILITIES | {Capability.LAYOUT}


class DrawioOrderedAdapter:
    name = "drawio_ordered"

    def build_slots(self, doc: TemplateDocument, model: DrawioModel) -> SlotMap:
        groups = iter_label_groups(doc.root)
        matched = align(labelled_cells(model), groups)
        slots: list[Slot] = []
        for index, group in enumerate(groups):
            if not group.tokens:
                continue
            slots.append(
                make_slot(group, matched.get(index), find_shape(group.container))
            )

        cells = model.cells_by_id()
        offset = derive_offset(slots, cells)
        validate_geometry(slots, offset, cells)
        capabilities = _capabilities(slots, offset)
        slot_map = SlotMap(
            adapter=self.name, slots=slots, offset=offset, capabilities=capabilities
        )
        if Capability.EDGES in capabilities:
            rendered = map_edges_to_paths(
                doc.root, [c for c in model.cells() if c.is_edge], cells, offset
            )
            slot_map.edges = attach_edges(
                slots,
                cells,
                {edge_id: r.path for edge_id, r in rendered.items()},
                {edge_id: r.markers for edge_id, r in rendered.items()},
            )
            unmatched = sum(1 for c in cells.values() if c.is_edge) - len(rendered)
            if unmatched:
                slot_map.notices.append(
                    f"{unmatched} edge(s) have no rendered line (not followed)"
                )
        unaligned = sum(1 for slot in slots if slot.cell is None)
        if unaligned:
            slot_map.notices.append(f"{unaligned} label(s) not aligned to a model cell")
        return slot_map


if __name__ == "__main__":
    pass
