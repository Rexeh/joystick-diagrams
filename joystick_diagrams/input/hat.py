"""Basic Hat structure for the Joystick DIagrams input library"""

from dataclasses import dataclass
from enum import Enum, auto


@dataclass
class Hat:
    id: int
    direction: "HatDirection"

    def __post_init__(self):
        if not isinstance(self.id, int):
            raise ValueError("Hat Switch must have an ID of int")

        if not isinstance(self.direction, HatDirection):
            raise ValueError("Invalid HatDirection used for hat switch")


class HatDirection(Enum):
    U = auto()
    UR = auto()
    R = auto()
    DR = auto()
    D = auto()
    DL = auto()
    L = auto()
    UL = auto()
