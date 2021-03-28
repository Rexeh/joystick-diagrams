'''Starship Citizen XML Parser for use with Joystick Diagrams'''
from xml.dom import minidom
import functions.helper as helper
import adaptors.joystick_diagram_interface as jdi
import os
from pathlib import Path

class StarshipCitizen(jdi.JDinterface):

    def __init__(self, file_path):
        jdi.JDinterface.__init__(self)
        
        self.file_path = file_path
        self.data = self.__load_file()
        self.hat_formats = {
            'up': "U",
            'down': "D",
            'left': "L",
            'right': "R"
        }

        self.hat = None
        self.devices = {}
        self.button_array = {}


    def __load_file(self):
        if os.path.exists(self.file_path):
            if (os.path.splitext(self.file_path))[1] == '.xml':
                data = Path(self.file_path).read_text(encoding="utf-8")
                if self.__validate_file(data):
                    return data
                else:
                    raise Exception("File is not a valid Starcraft Citizen XML")
            else:
                raise Exception("File must be an XML file")
        else:
            raise FileNotFoundError("File not found")

    def __validate_file(self, data):
        try:
            parsed_xml = minidom.parseString(data)
            if (len(parsed_xml.getElementsByTagName('devices'))==1 and
                len(parsed_xml.getElementsByTagName('options'))>0 and
                len(parsed_xml.getElementsByTagName('actionmap'))>0):
                return True
            else:
                return False
        except:
            return False


    def parse_map(self, map):
        segments = map.split("_")

        bind_device = segments[0]
        device_object = self.get_stored_device(bind_device)

        print(segments)

        # TODO
        # SLIDERS
        # AXIS

        if segments[1] == ' ':
            print("Blank")
            c_map = None
            return (device_object,c_map)
        elif segments[1][0:6] == 'button':
            print("Button")
            button_id = segments[1][6:]
            print(button_id)
            c_map = 'BUTTON_{id}'.format(id=button_id)
            return (device_object,c_map)
        elif segments[1][0:3] == 'hat':
            print("Hat Switch")
            pov_id = segments[1][3:]
            print(pov_id)
            pov_dir = self.convert_hat_format(segments[2])
            print(pov_dir)
            c_map = 'POV_{id}_{dir}'.format(id=pov_id,dir=pov_dir)
            return (device_object,c_map)
        else:
            c_map = None
            return (device_object,c_map)
   
    def get_human_readable_name(self):
        # Future for str replacements
        pass
    
    def convert_hat_format(self, hat):
        #TODO
        #Unknown HAT maps for UR/DR etc
        return self.hat_formats[hat]

    def extract_device_information(self, option):
        ''' Accepts parsed OPTION from Starship Citizen XML'''

        name = (option.getAttribute('Product')[0:(len(option.getAttribute('Product'))-38)]).strip()
        guid = option.getAttribute('Product')[-37:-2] #GUID Fixed
        return {
            'name': name,
            'guid' : guid
            }

    def get_stored_device(self, device):
        return self.devices[device]

    def add_device(self, option):
        ''' Accepts parsed OPTION from Starship Citizen XML'''
        self.devices.update({
            self.device_id(option.getAttribute('type'),option.getAttribute('instance')) : self.extract_device_information(option)
        })

    def process_name(self, name):
        name = name.split("_")
        if len(name) == 1:
            return name[0].capitalize()
        else:
            return (" ".join(name)).capitalize()

    def build_button_map(self, device,button, name):
        if (device in self.button_array):
            self.button_array[device].update( {button:name } )
        else:
            self.button_array.update({
                device : {
                    button : name
                }
            })

    def device_id(self, device_type, instance):
        if device_type == 'keyboard':
            t = "kb"
        elif device_type == 'joystick':
            t = "js"
        else:
            t = "mo"
        return "{type}{instance}".format(type=t, instance=instance)

    def parse(self):
        parse = minidom.parseString(self.data)
        joysticks = parse.getElementsByTagName('options')
        for j in joysticks:
            self.add_device(j)
            print(j.getAttribute('type'))
            print(j.getAttribute('instance'))
            print(j.getAttribute('Product'))
        actions = parse.getElementsByTagName('actionmap')

        for i in actions:
            print("-----------")
            print("Category: {}".format(self.process_name(i.getAttribute('name'))))
            single_actions = i.getElementsByTagName('action')
            for action in single_actions:
                name = self.process_name(action.getAttribute('name'))
                print(name)
                binds = action.getElementsByTagName('rebind')
                bind = binds[0].getAttribute('input')
                button = self.parse_map(bind)
                if(button and button[1] is not None):
                    print("Button Found: {}".format(button[1]))
                    self.build_button_map(button[0]['name'], button[1], name)
                else:
                    print("Button Not found {}".format(button))
                print("-----------")

        for item in self.button_array:
            self.update_joystick_dictionary(item, "Default", False, self.button_array[item])

        return self.joystick_dictionary
