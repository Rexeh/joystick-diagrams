import logging

_logger = logging.getLogger(__name__)


class JDinterface:
    def __init__(self):
        self.no_bind_text = "NO BIND"
        self.joystick_dictionary = {}

    def update_joystick_dictionary(self, device, mode, inherit, buttons):
        data = {"Buttons": buttons, "Axis": "", "Inherit": inherit}

        if device in self.joystick_dictionary:
            if mode in self.joystick_dictionary[device]:
                self.joystick_dictionary[device][mode].update(data)
            else:
                self.joystick_dictionary[device].update({mode: data})
        else:
            self.joystick_dictionary.update({device: {mode: data}})

    def inherit_joystick_dictionary(self):
        for item in self.joystick_dictionary:
            for profile in self.joystick_dictionary[item]:
                if self.joystick_dictionary[item][profile]["Inherit"]:
                    _logger.debug("{} Profile has inheritance in mode {}".format(item, profile))
                    _logger.debug("Profile inherits from {}".format(self.joystick_dictionary[item][profile]["Inherit"]))
                    inherit = self.joystick_dictionary[item][profile]["Inherit"]
                    inherited_profile = self.joystick_dictionary[item][inherit]
                    _logger.debug("Inherited Profile Contains {}".format(inherited_profile))
                    _logger.debug(
                        "Starting Profile Contains {}".format(self.joystick_dictionary[item][profile]["Buttons"])
                    )
                    for button, desc in inherited_profile["Buttons"].items():
                        check_button = button in self.joystick_dictionary[item][profile]["Buttons"]
                        if not check_button:
                            self.joystick_dictionary[item][profile]["Buttons"].update({button: desc})
                        elif self.joystick_dictionary[item][profile]["Buttons"][button] == self.no_bind_text:
                            self.joystick_dictionary[item][profile]["Buttons"][button] = desc
                    _logger.debug(
                        "Ending Profile Contains {}".format(self.joystick_dictionary[item][profile]["Buttons"])
                    )
