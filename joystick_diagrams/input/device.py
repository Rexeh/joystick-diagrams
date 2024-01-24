import functools
import logging
from operator import call

from joystick_diagrams.input import button
from joystick_diagrams.input.axis import Axis, AxisDirection, AxisSlider
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
    INPUT_BUTTON_KEY: "id",
    INPUT_AXIS_KEY: "id.name",
    INPUT_AXIS_SLIDER_KEY: "id",
    INPUT_HAT_KEY: "id",
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
        resolved_type = CLASS_MAP[type(control)]
        return resolved_type

    def create_axis(self, control: Axis, command: str):
        input = self.get_input(
            input_type=INPUT_AXIS_KEY, input_id=getattr(control, INPUT_TYPE_IDENTIFIERS.get(INPUT_AXIS_KEY))
        )
        pass

    def create_button(self, control: Button, command: str):
        input = self.get_input(
            input_type=INPUT_BUTTON_KEY, input_id=getattr(control, INPUT_TYPE_IDENTIFIERS.get(INPUT_BUTTON_KEY))
        )

        if input:
            input.command = command
        else:
            self.inputs[INPUT_BUTTON_KEY][control.id] = Input_(control, command)
        pass

    def create_hat(self, control: Hat, command: str):
        input = self.get_input(
            input_type=INPUT_HAT_KEY, input_id=getattr(control, INPUT_TYPE_IDENTIFIERS.get(INPUT_HAT_KEY))
        )
        pass

    def create_axis_slider(self, control: AxisSlider, command: str):
        input = self.get_input(
            input_type=INPUT_AXIS_SLIDER_KEY,
            input_id=getattr(control, INPUT_TYPE_IDENTIFIERS.get(INPUT_AXIS_SLIDER_KEY)),
        )

        pass

    CLASS_FUNCS = {Button: create_button, Axis: create_axis, Hat: create_hat, AxisSlider: create_axis_slider}

    def get_input(self, input_type: str, input_id: str | int) -> Input_ | None:
        return self.inputs[input_type].get(input_id)

    def get_inputs(self) -> dict[str, dict[str | int, Input_]]:
        return self.inputs

    def add_modifier_to_input(self, control: Axis | Button | Hat | AxisSlider, modifier: set, command: str) -> None:
        """Adds a modifier to a respective control type supplied.

        Creates an input if it  does not exist, otherwise attaches a modifier
        """
        _logger.debug(f"Adding modifier {modifier} to input {control}")

        # Magic
        type_key = self.resolve_type(control)

        input = self.get_input(
            type_key,
            getattr(control, INPUT_TYPE_IDENTIFIERS[type_key]),
        )

        if input is None:
            _logger.warning(
                f"Modifier attempted to be added to {control} but input does not exist. So a shell will be created"
            )

            # Find the control objects respective create function
            object_create_function = functools.partial(self.CLASS_FUNCS[type(control)], self)

            # Create the control object
            object_create_function(control, command="")

            shell_input = self.get_input(
                type_key,
                getattr(control, INPUT_TYPE_IDENTIFIERS[type_key]),
            )

            if shell_input:
                shell_input.add_modifier(modifier, command)

        else:
            input.add_modifier(modifier, command)


if __name__ == "__main__":
    dev = Device_("guid1", "Potato")

    dev.create_button(Button(1), "shoot")

    dev.create_button(Button(2), "shoot")

    dev.create_button(Button(1), "potato")

    print(dev.inputs["buttons"])

    dev.add_modifier_to_input(Button(6), {"ctrl"}, "modifier")

    print(dev.inputs["buttons"])
