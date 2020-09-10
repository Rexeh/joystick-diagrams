from xml.dom import minidom
import functions.helper as helper

class Gremlin:
## Adaptor for Joystick Gremlin

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
        self.inherit = None
        self.buttons = None
        self.buttonArray = None
        self.formattedButtons = None
        
    def createDictionary(self):
        self.formattedButtons = {}
        self.devices = self.getDevices()
        helper.log("Number of Devices: ",str(self.devices.length))
        self.formattedButtons = {}
        for self.device in self.devices:
            self.currentdevice = self.getSingleDevice()
            self.modes = self.getDeviceModes()
            helper.log("All Modes: ",self.modes)
            for self.mode in self.modes:
                # Does this mode Inherit?
                self.currentInherit = self.hasInheritance()
                self.buttonArray = {}
                self.currentMode = self.getSingleMode()
     
                helper.log("Selected Mode: ",self.currentMode)
                
                self.buttons = self.getModeButtons()
                self.extractButtons()
                helper.updateDeviceArray(self.formattedButtons ,self.currentdevice,self.currentMode,self.buttonArray)
        return self.formattedButtons

    def getDevices(self):
        return self.file.getElementsByTagName('device')

    def getModeButtons(self):
        return self.mode.getElementsByTagName('button')

    def getDeviceModes(self):
        return self.device.getElementsByTagName('mode')

    def getSingleDevice(self):
        return self.device.getAttribute('name')

    def getInheritedMode(self):
        pass

    def getSingleMode(self):
        return self.mode.getAttribute('name')

    def hasInheritance(self):
        inherit = self.mode.getAttribute('inherit')
        
        print(inherit)
        if inherit != '':
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
