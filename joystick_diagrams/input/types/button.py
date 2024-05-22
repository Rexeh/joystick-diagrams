"""Basic Button structure for the Joystick DIagrams input library"""

from dataclasses import dataclass

from joystick_diagrams.input.types.control import JoystickDiagramControl


@dataclass
class Button(JoystickDiagramControl):
    id: int

    def __post_init__(self):
        if not isinstance(self.id, int):
            raise ValueError("Button must be identified by integer")

    @property
    def identifier(self):
        return f"BUTTON_{self.id}"
