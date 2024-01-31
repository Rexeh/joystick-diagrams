"""Joystick Diagrams Input Module

This module contains access to the creation and tracking of devices and their inputs

Not intended to be used directly, but via the Device class helper methods
"""

import logging

from joystick_diagrams.input.axis import Axis, AxisDirection, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat
from joystick_diagrams.input.modifier import Modifier

_logger = logging.getLogger(__name__)

CONTROL_TYPES = (Axis, Button, Hat, AxisSlider)


class Input_:
    def __init__(self, control: Axis | Button | Hat | AxisSlider, command: str) -> None:
        self.input_control = control
        self.command = command
        self.modifiers: list[Modifier] = []

    def __repr__(self):
        return f"{self.input_control} - {self.command} - {self.modifiers}"

    def __str__(self):
        mod_to_string = [x.__str__() for x in self.modifiers]
        return f"{self.command} - {str(mod_to_string)}"

    def __post_init__(self):
        if not isinstance(self.input_control, CONTROL_TYPES):
            raise ValueError("Input identifier must be a valid control type.")

    @property
    def identifier(self):
        "Returns the child control identifier"
        return self.input_control.identifier

    def add_modifier(self, modifier: set, command: str) -> None:
        """Adds a modifier to an existing input, or amends an existing modifier"""
        existing = self._check_existing_modifier(modifier)

        _logger.info(f"Existing modifier check is {existing}")

        if existing is None:
            _logger.info(f"Modifier {modifier} for input {self.input_control} not found so adding")
            self.modifiers.append(Modifier(modifier, command))
        else:
            _logger.info(f"Modifier {modifier} already exists for {self.input_control} and command has been overidden")
            existing.command = command

    def _check_existing_modifier(self, modifier: set) -> Modifier | None:
        _logger.debug(f"Existing modifiers: {self.modifiers}")
        for x in self.modifiers:
            _logger.debug(f"Checking for existing modifier {modifier} in {x}")
            if x.modifiers == modifier:
                _logger.debug(f"Modifier already  exists {x}")
                return x
        return None


if __name__ == "__main__":
    input = Input_(Axis(AxisDirection.X), "Fly up")

    print(input)
