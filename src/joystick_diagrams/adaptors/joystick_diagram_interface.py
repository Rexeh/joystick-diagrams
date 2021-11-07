import joystick_diagrams.functions.helper as helper


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
                    helper.log(
                        "{} Profile has inheritance in mode {}".format(item, profile),
                        "debug",
                    )
                    helper.log(
                        "Profile inherits from {}".format(self.joystick_dictionary[item][profile]["Inherit"]),
                        "debug",
                    )
                    inherit = self.joystick_dictionary[item][profile]["Inherit"]
                    inherited_profile = self.joystick_dictionary[item][inherit]
                    helper.log(
                        "Inherited Profile Contains {}".format(inherited_profile),
                        "debug",
                    )
                    helper.log(
                        "Starting Profile Contains {}".format(self.joystick_dictionary[item][profile]["Buttons"]),
                        "debug",
                    )
                    for button, desc in inherited_profile["Buttons"].items():
                        check_button = button in self.joystick_dictionary[item][profile]["Buttons"]
                        if not check_button:
                            self.joystick_dictionary[item][profile]["Buttons"].update({button: desc})
                        elif self.joystick_dictionary[item][profile]["Buttons"][button] == self.no_bind_text:
                            self.joystick_dictionary[item][profile]["Buttons"][button] = desc
                    helper.log(
                        "Ending Profile Contains {}".format(self.joystick_dictionary[item][profile]["Buttons"]),
                        "debug",
                    )
