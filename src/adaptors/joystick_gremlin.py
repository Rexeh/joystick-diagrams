'''Joystick Gremlin (Version ~13) XML Parser for use with Joystick Diagrams'''
from xml.dom import minidom
import functions.helper as helper
import adaptors.joystick_diagram_interface as jdi

class JoystickGremlin(jdi.JDinterface):

    def __init__(self,filepath):
    ## TRY FIND PATH
        jdi.JDinterface.__init__(self)
        self.file = self.parse_xml_file(filepath)
        
        # New Attributes
        self.device_names = self.get_device_names()
        self.profiles = []
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
        self.inheritModes = {}
        self.usingInheritance = False
        self. position_map = {
        1 : 'U',
        2 : 'UR',
        3 : 'R',
        4 : 'DR',
        5 : 'D',
        6 : 'DL',
        7 : 'L',
        8 : 'UL'
    }


    def get_device_names(self):
        self.devices = self.getDevices()
        deviceItems = []

        for item in self.devices:
            deviceItems.append(item.getAttribute('name'))
        return deviceItems

    def get_modes(self):
        self.devices = self.getDevices()
        profile_modes = []

        item = self.devices[0] # All Modes common across JG
        modes = item.getElementsByTagName('mode')
        for mode in modes:
            mode_name = mode.getAttribute('name')
            profile_modes.append(mode_name)
        return profile_modes

    def parse_xml_file(self, xml_file):
        ## Improve loading of file, checks for validity etc
        return minidom.parse(xml_file)

    def createDictionary(self, profiles=[]):
        self.profiles = profiles
        self.devices = self.getDevices()
        helper.log("Number of Devices: {}".format(str(self.devices.length)), 'debug')

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
                self.hats = self.getModeHats()
                self.extractButtons()
                self.extractHats()
                self.update_joystick_dictionary(self.currentdevice,
                                    self.currentMode,
                                    self.currentInherit,
                                    self.buttonArray
                                    )
        if self.usingInheritance:
            self.inherit_joystick_dictionary()
            self.filter_dictionary()
            return self.joystick_dictionary
        else:
            self.filter_dictionary()
            return self.joystick_dictionary

    def filter_dictionary(self):
        if len(self.profiles)>0:
            for key,value in self.joystick_dictionary.items():
                for item in value.copy():
                    if not item in self.profiles:
                        self.joystick_dictionary[key].pop(item,None)
        return self.joystick_dictionary

    def getDevices(self):
        return self.file.getElementsByTagName('device')

    def getModeButtons(self):
        return self.mode.getElementsByTagName('button')

    def getModeHats(self):
        return self.mode.getElementsByTagName('hat')

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

    def extractHats(self):

        ## TODO Tests
        for i in self.hats:
            hat_id = i.getAttribute('id')
            print("Hat ID: {}".format(hat_id))

            if i.getAttribute('description'):
                hat_description = i.getAttribute('description')
                print("Hat has description: {}".format(hat_description))
            else:
                hat_description = ''

            hat_containers = i.getElementsByTagName('container')

            if(hat_containers):
                print("Has containers: {}".format(hat_containers.length))

                for c in hat_containers:
                    
                    hat_positions = c.getElementsByTagName('action-set')
                    hat_count = hat_positions.length
                    increment = 8/hat_count
                    pos = 1
                    print("We have {} hat positions".format(hat_count))

                    for hp in hat_positions:

                        if hp.getElementsByTagName('description'):
                            # Ignore more than 1 description. always use first
                            hat_direction_description = hp.getElementsByTagName('description')[0].getAttribute('description')
                        else:
                            hat_direction_description = hat_description
                        print(self.position_map[pos])

                        self.buttonArray.update ({
                        'POV_{ID}_{DIR}'.format(
                            ID=i.getAttribute('id'),
                            DIR=self.position_map[pos]
                            ):str(hat_direction_description)
                        })

                        pos = pos + increment

        
    

    def getDeviceCount(self):
        return self.file.getElementsByTagName('device').length
