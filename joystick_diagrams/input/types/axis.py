"""Basic AXIS structure for the Joystick DIagrams input library

Handles AXIS and Axis Slider control types
"""

from dataclasses import dataclass
from enum import Enum, auto

from joystick_diagrams.input.types.control import JoystickDiagramControl


@dataclass
class Axis(JoystickDiagramControl):
    id: "AxisDirection"

    def __post_init__(self):
        if not isinstance(self.id, AxisDirection):
            raise ValueError("Invalid direction used for AXIS")

    @property
    def identifier(self):
        return f"AXIS_{self.id.name}"


class AxisDirection(Enum):
    X = auto()
    Y = auto()
    Z = auto()
    RX = auto()
    RY = auto()
    RZ = auto()
    SLIDER = auto()


@dataclass
class AxisSlider(JoystickDiagramControl):
    id: int

    def __post_init__(self):
        if not isinstance(self.id, int):
            raise ValueError("A slider must have an id of INT")

    @property
    def identifier(self):
        return f"AXIS_SLIDER_{self.id}"
