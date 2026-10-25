"""Adapter detection (plan §4.1).

1. Any ``g[@data-cell-id]`` in the rendered SVG → ``DrawioCellIdAdapter``.
2. Otherwise a draw.io model with labelled vertex cells → ``DrawioOrderedAdapter``.
3. A draw.io model without labelled cells → ``TextOnlyAdapter``.

Valid XML that is not draw.io never reaches detection: ``DrawioModel.from_content``
raises and the pipeline falls back to the legacy engine (GenericSvgAdapter deferred).
"""

from __future__ import annotations

from joystick_diagrams.render.adapters._common import SVG
from joystick_diagrams.render.adapters.base import TemplateAdapter
from joystick_diagrams.render.adapters.drawio_cell_id import DrawioCellIdAdapter
from joystick_diagrams.render.adapters.drawio_ordered import (
    DrawioOrderedAdapter,
    labelled_cells,
)
from joystick_diagrams.render.adapters.text_only import TextOnlyAdapter
from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.drawio_model import DrawioModel


def has_cell_ids(doc: TemplateDocument) -> bool:
    return any(g.get("data-cell-id") is not None for g in doc.root.iter(f"{SVG}g"))


def detect_adapter(doc: TemplateDocument, model: DrawioModel) -> TemplateAdapter:
    if has_cell_ids(doc):
        return DrawioCellIdAdapter()
    if labelled_cells(model):
        return DrawioOrderedAdapter()
    return TextOnlyAdapter()


__all__ = [
    "DrawioCellIdAdapter",
    "DrawioOrderedAdapter",
    "TemplateAdapter",
    "TextOnlyAdapter",
    "detect_adapter",
    "has_cell_ids",
]
