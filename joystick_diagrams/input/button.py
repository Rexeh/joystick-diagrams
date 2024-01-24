"""Basic Button structure for the Joystick DIagrams input library"""

from dataclasses import dataclass


@dataclass
class Button:
    id: int

    def __post_init__(self):
        if not isinstance(self.id, int):
            raise ValueError("Button must be identified by integer")
