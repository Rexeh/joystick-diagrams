from dataclasses import dataclass, field

from joystick_diagrams.input import device
from joystick_diagrams.input.device import Device_
from joystick_diagrams.profile_wrapper import ProfileWrapper
from joystick_diagrams.template import Template


@dataclass
class ExportDevice:
    "An ExportDevice packages a given Device_ with its configured Template and origin profile wrapper description."

    device: Device_
    _template: Template | None
    profile_wrapper: ProfileWrapper
    errors: set = field(default_factory=set, init=False)

    @property
    def template_file_name(self):
        return self._template.template_file_name

    @property
    def device_id(self):
        return self.device.guid

    @property
    def device_name(self):
        return self.device.name

    @property
    def has_template(self) -> bool:
        return bool(self.template)

    @property
    def template(self):
        return self._template

    @template.setter
    def template(self, value):
        self._template = value

        if value is not None:
            self.check_compatibility()

    def check_compatibility(self):
        """Computes mergeability of a Device to the Template.

        Returns list of missing controls from TEMPLATE
        """
        device_inputs = self.device.get_inputs()

        # Button Checks
        device_buttons = {
            x.lower() for x in set(device_inputs.get(device.INPUT_BUTTON_KEY))
        }

        device_buttons.difference_update(self.template.get_template_buttons())

        # Hat Checks
        device_hats = {x.lower() for x in set(device_inputs.get(device.INPUT_HAT_KEY))}
        device_hats.difference_update(self.template.get_template_hats())

        # AXIS
        device_axis = {x.lower() for x in set(device_inputs.get(device.INPUT_AXIS_KEY))}
        device_axis = device_axis.union(
            {x.lower() for x in set(device_inputs.get(device.INPUT_AXIS_SLIDER_KEY))}
        )
        device_axis.difference_update(self.template.get_template_axis())

        self.errors = self.errors.union(device_buttons, device_hats, device_axis)


if __name__ == "__main__":
    pass
