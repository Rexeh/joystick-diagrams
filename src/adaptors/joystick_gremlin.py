'''Joystick Gremlin (Version ~13) XML Parser for use with Joystick Diagrams'''
from xml.dom import minidom
import functions.helper as helper
import adaptors.joystick_diagram_interface as jdi

class JoystickGremlin(jdi.JDinterface):

    def __init__(self,filepath):
    ## TRY FIND PATH
        jdi.JDinterface.__init__(self)
        self.file = minidom.parse(filepath) ## Remove from instantiation > Make testable function with error handling (FolloW DCS_World Pattern)
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
                self.updateJoystickDictionary(self.currentdevice,
                                    self.currentMode,
                                    self.currentInherit,
                                    self.buttonArray
                                    )
        if self.usingInheritance:
            self.inheritJoystickDictionary()
            return self.joystick_dictionary
        else:
            return self.joystick_dictionary

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
