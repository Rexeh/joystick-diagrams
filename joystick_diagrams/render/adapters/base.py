"""Adapter protocol: how a template's rendered SVG maps onto its draw.io model.

An adapter only builds the ``SlotMap``. It never changes text; text replacement
is done by the pipeline over every text node, so a mis-aligned adapter can only
cost styling/layout capabilities, never produce wrong text (plan principle 3).
"""

from __future__ import annotations

from typing import Protocol

from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.slots import SlotMap


class TemplateAdapter(Protocol):
    name: str

    def build_slots(self, doc: TemplateDocument, model: DrawioModel) -> SlotMap: ...


if __name__ == "__main__":
    pass
