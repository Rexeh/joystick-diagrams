"""Basic modifier structure for the Joystick DIagrams input library"""

from dataclasses import dataclass


@dataclass
class Modifier:
    modifiers: set[str]
    command: str

    def __post_init__(self):
        if not isinstance(self.modifiers, set):
            raise ValueError("Modifiers must be a set")

        if not isinstance(self.command, str):
            raise ValueError("A modifier command must be a string")

    def __str__(self):
        flattened_mods = "+".join(list(self.modifiers))
        return f"{self.command} - {str(flattened_mods)}"
