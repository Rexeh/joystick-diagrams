"""Handles representation of a Device in the context of a Profile.

- Devices are responsible for keeping track of their Inputs
"""

import logging
from typing import Union

from joystick_diagrams.input.axis import Axis, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat
from joystick_diagrams.input.input import Input_

_logger = logging.getLogger("__name__")

INPUT_BUTTON_KEY = "buttons"
INPUT_AXIS_KEY = "axis"
INPUT_AXIS_SLIDER_KEY = "axis_slider"
INPUT_HAT_KEY = "hats"

CLASS_MAP = {Button: INPUT_BUTTON_KEY, Axis: INPUT_AXIS_KEY, AxisSlider: INPUT_AXIS_SLIDER_KEY, Hat: INPUT_HAT_KEY}

INPUT_TYPE_IDENTIFIERS = {
    INPUT_BUTTON_KEY: "identifier",
    INPUT_AXIS_KEY: "identifier",
    INPUT_AXIS_SLIDER_KEY: "identifier",
    INPUT_HAT_KEY: "identifier",
}


class Device_:
    def __init__(self, guid: str, name: str):
        self.guid = guid.strip().lower()
        self.name = name.strip()

        self.inputs: dict[str, dict[str | int, Input_]] = {
            INPUT_BUTTON_KEY: {},
            INPUT_AXIS_KEY: {},
            INPUT_AXIS_SLIDER_KEY: {},
            INPUT_HAT_KEY: {},
        }

    def resolve_type(self, control: Axis | Button | Hat | AxisSlider) -> str:
        """Resolves a given input control to its corresponding dictionary key"""
        resolved_type = CLASS_MAP.get(type(control))

        if not resolved_type:
            raise ValueError(f"Only valid control types can be used - {CLASS_MAP.keys()}")

        return resolved_type

    def create_input(self, control: Union[Axis, Button, Hat, AxisSlider], command: str) -> None:
        """Creates an input in the Device inputs dictionary where one does not exist.

        Where input already exists, the input command is updated

        Returns None | ValueError
        """
        control_key = self.resolve_type(control)

        input_obj = self.get_input(
            input_type=control_key, input_id=getattr(control, INPUT_TYPE_IDENTIFIERS[control_key])
        )
        if input_obj:
            input_obj.command = command
        else:
            self.inputs[control_key][getattr(control, INPUT_TYPE_IDENTIFIERS[control_key])] = Input_(control, command)

    def get_input(self, input_type: str, input_id: str | int) -> Input_ | None:
        """Get an input for a specific input type.

        Returns None | Input_
        """
        return self.inputs[input_type].get(input_id)

    def get_inputs(self) -> dict[str, dict[str | int, Input_]]:
        """Returns input dictionary

        Returns dict
        """
        return self.inputs

    def get_combined_inputs(self) -> dict:
        """Returns a flattened input dictionary

        Returns dict
        """
        flattened_dict_ = {}
        for value in self.inputs.values():
            flattened_dict_.update(value)
        return flattened_dict_

    def add_modifier_to_input(self, control: Axis | Button | Hat | AxisSlider, modifier: set, command: str) -> None:
        """Adds a modifier to a respective control type supplied.

        Creates an input if it does not exist, otherwise attaches a modifier

        Returns:  None
        """
        _logger.debug(f"Adding modifier {modifier} to input {control}")

        # Magic
        type_key = self.resolve_type(control)

        input_obj = self.get_input(
            type_key,
            getattr(control, INPUT_TYPE_IDENTIFIERS[type_key]),
        )

        if input_obj is None:
            _logger.warning(
                f"Modifier attempted to be added to {control} but input does not exist. So a shell will be created"
            )

            # Create the control object
            self.create_input(control, command="")

            shell_input = self.get_input(
                type_key,
                getattr(control, INPUT_TYPE_IDENTIFIERS[type_key]),
            )

            if shell_input:
                shell_input.add_modifier(modifier, command)

        else:
            input_obj.add_modifier(modifier, command)


if __name__ == "__main__":
    inputs = {
        INPUT_BUTTON_KEY: {"abs": "x"},
        INPUT_AXIS_KEY: {"abd": "x"},
        INPUT_AXIS_SLIDER_KEY: {},
        INPUT_HAT_KEY: {},
    }
