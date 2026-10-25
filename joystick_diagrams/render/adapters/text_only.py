"""Text-only adapter: slots from rendered labels alone, no model alignment.

Used when the model decodes but offers nothing to align against (no labelled
vertex cells). Capabilities are TEXT and TEXT_STYLE only.
"""

from __future__ import annotations

from joystick_diagrams.render.adapters._common import (
    find_shape,
    iter_label_groups,
    make_slot,
)
from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.slots import Capability, SlotMap

TEXT_ONLY_CAPABILITIES = frozenset({Capability.TEXT, Capability.TEXT_STYLE})


class TextOnlyAdapter:
    name = "text_only"

    def build_slots(self, doc: TemplateDocument, model: DrawioModel) -> SlotMap:
        slots = [
            make_slot(group, None, find_shape(group.container))
            for group in iter_label_groups(doc.root)
            if group.tokens
        ]
        return SlotMap(
            adapter=self.name, slots=slots, capabilities=TEXT_ONLY_CAPABILITIES
        )


if __name__ == "__main__":
    pass
