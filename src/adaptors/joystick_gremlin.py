from xml.dom import minidom
import functions.helper as helper

class JoystickGremlin:
    no_bind_text = "NO BIND"

    def __init__(self,filepath):
    ## TRY FIND PATH
        self.file = minidom.parse(filepath)
        self.modes = None
        self.mode = None
        self.devices = None
        self.device = None
        self.currentdevice = None
        self.currentMode = None
        self.currentInherit = None
        self.inherit = None
        self.buttons = None
        self.buttonArray = None
        self.formattedButtons = None
        self.inheritModes = {}
        self.usingInheritance = False

    def createDictionary(self):
        self.formattedButtons = {}
        self.devices = self.getDevices()
        helper.log("Number of Devices: {}".format(str(self.devices.length)), 'debug')
        self.formattedButtons = {}

        for self.device in self.devices:
            self.currentdevice = self.getSingleDevice()
            self.modes = self.getDeviceModes()
            helper.log("All Modes: {}".format(self.modes))
            for self.mode in self.modes:
                self.currentInherit = self.hasInheritance()
                self.buttonArray = {}
                self.currentMode = self.getSingleMode()
                helper.log("Selected Mode: {}".format(self.currentMode), 'debug')
                self.buttons = self.getModeButtons()
                self.extractButtons()
                helper.updateDeviceArray(
                                    self.formattedButtons,
                                    self.currentdevice,
                                    self.currentMode,
                                    self.currentInherit,
                                    self.buttonArray
                                    )
        if self.usingInheritance:
            self.inheritProfiles()
            return self.formattedButtons
        else:
            return self.formattedButtons

    def inheritProfiles(self):
        for item in self.formattedButtons:
            for profile in self.formattedButtons[item]:
                if self.formattedButtons[item][profile]['Inherit']:
                    helper.log("{} Profile has inheritance in mode {}".format(item,profile), 'debug')
                    helper.log("Profile inherits from {}".format(self.formattedButtons[item][profile]['Inherit']), 'debug')
                    inherit = self.formattedButtons[item][profile]['Inherit']
                    inheritConfig = self.formattedButtons[item][inherit]
                    helper.log("Inherited Profile Contains {}".format(inheritConfig), 'debug')
                    helper.log("Starting Profile Contains {}".format(self.formattedButtons[item][profile]['Buttons']), 'debug')
                    for button, desc in inheritConfig['Buttons'].items():
                        checkButton = button in self.formattedButtons[item][profile]['Buttons']
                        if checkButton == False:
                            self.formattedButtons[item][profile]['Buttons'].update({
                                                        button:desc
                                                        })
                        elif self.formattedButtons[item][profile]['Buttons'][button] == self.no_bind_text:
                            self.formattedButtons[item][profile]['Buttons'][button] = desc
                    helper.log("Ending Profile Contains {}".format(self.formattedButtons[item][profile]['Buttons']), 'debug')

    def getDevices(self):
        return self.file.getElementsByTagName('device')

    def getModeButtons(self):
        return self.mode.getElementsByTagName('button')

    def getDeviceModes(self):
        return self.device.getElementsByTagName('mode')

    def getSingleDevice(self):
        return self.device.getAttribute('name')

    def getSingleMode(self):
        return self.mode.getAttribute('name')

    def hasInheritance(self):
        inherit = self.mode.getAttribute('inherit')
        if inherit != '':
            if self.usingInheritance != True:
                self.usingInheritance = True
            return inherit
        else:
            return False

    def inheritedModes(self):
        return self.mode.getAttribute('name')

    def extractButtons(self):
        for i in self.buttons:
            if i.getAttribute('description') != "":
                self.buttonArray.update ({
                "BUTTON_" + str(i.getAttribute('id')):str(i.getAttribute('description'))
                })
            else:
                self.buttonArray.update ({
                "BUTTON_" + str(i.getAttribute('id')): self.no_bind_text
                })
        return self.buttonArray

    def getDeviceCount(self):
        return self.file.getElementsByTagName('device').length
