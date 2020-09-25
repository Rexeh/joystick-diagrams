'''Interface for Joystick Diagrams'''
class JDinterface:

    def __init__(self):
        self.no_bind_text = "NO BIND"
        self.joystick_dictionary = {}

    def updateJoystickDictionary(self, device, mode, inherit, buttons):
        data = {
            "Buttons": buttons,
            "Axis": "",
            "Inherit": inherit}

        if device in self.joystick_dictionary:
            if mode in self.joystick_dictionary[device]:
                self.joystick_dictionary[device][mode].update(data)
            else:
                self.joystick_dictionary[device].update({
                        mode:   data
                            })
        else:
            self.joystick_dictionary.update({
                device : {
                    mode:   data
                                }
            })

    def inheritJoystickDictionary(self):
        for item in self.joystick_dictionary:
            for profile in self.joystick_dictionary[item]:
                if self.joystick_dictionary[item][profile]['Inherit']:
                    #helper.log("{} Profile has inheritance in mode {}".format(item,profile), 'debug')
                    #helper.log("Profile inherits from {}".format(self.joystick_dictionary[item][profile]['Inherit']), 'debug')
                    inherit = self.joystick_dictionary[item][profile]['Inherit']
                    inheritConfig = self.joystick_dictionary[item][inherit]
                    #helper.log("Inherited Profile Contains {}".format(inheritConfig), 'debug')
                    #helper.log("Starting Profile Contains {}".format(self.joystick_dictionary[item][profile]['Buttons']), 'debug')
                    for button, desc in inheritConfig['Buttons'].items():
                        checkButton = button in self.joystick_dictionary[item][profile]['Buttons']
                        if checkButton == False:
                            self.joystick_dictionary[item][profile]['Buttons'].update({
                                                        button:desc
                                                        })
                        elif self.joystick_dictionary[item][profile]['Buttons'][button] == self.no_bind_text:
                            self.joystick_dictionary[item][profile]['Buttons'][button] = desc
                    #helper.log("Ending Profile Contains {}".format(self.joystick_dictionary[item][profile]['Buttons']), 'debug')
    ## COMMON METHODS

    # SANETISE
    # Create Button Array
    