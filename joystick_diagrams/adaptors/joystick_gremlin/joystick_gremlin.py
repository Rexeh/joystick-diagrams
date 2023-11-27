"""Joystick Gremlin (Version ~13) XML Parser for use with Joystick Diagrams"""
import logging
from xml.dom import minidom

import joystick_diagrams.adaptors.joystick_diagram_interface as jdi

_logger = logging.getLogger(__name__)


class JoystickGremlin(jdi.JDinterface):
    def __init__(self, filepath):
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
        self.current_device = None
        self.current_mode = None
        self.current_inherit = None
        self.inherit = None
        self.buttons = None
        self.button_array = None
        self.inherit_modes = {}
        self.using_inheritance = False
        self.position_map = {
            1: "U",
            2: "UR",
            3: "R",
            4: "DR",
            5: "D",
            6: "DL",
            7: "L",
            8: "UL",
        }
        self.hats = None

    def get_device_names(self) -> list:
        self.devices = self.get_devices()
        device_items = []

        for item in self.devices:
            device_items.append(item.getAttribute("name"))
        return device_items

    def get_modes(self) -> list:
        self.devices = self.get_devices()
        profile_modes = []

        item = self.devices[0]  # All Modes common across JG
        modes = item.getElementsByTagName("mode")
        for mode in modes:
            mode_name = mode.getAttribute("name")
            profile_modes.append(mode_name)
        return profile_modes

    def parse_xml_file(self, xml_file) -> minidom.Document:
        ## Improve loading of file, checks for validity etc
        return minidom.parse(xml_file)

    def create_dictionary(self, profiles=None) -> dict:
        self.profiles = profiles
        self.devices = self.get_devices()
        _logger.debug(f"Number of Devices: {self.devices.length}")

        for self.device in self.devices:
            self.current_device = self.get_single_device()
            self.modes = self.get_device_modes()
            _logger.debug(f"All Modes: {self.modes}")
            for self.mode in self.modes:
                self.current_inherit = self.has_inheritance()
                self.button_array = {}
                self.current_mode = self.get_single_mode()
                _logger.debug(f"Selected Mode: {self.current_mode}")
                self.buttons = self.get_mode_buttons()
                self.hats = self.get_mode_hats()
                self.extract_buttons()
                self.extract_hats()
                self.update_joystick_dictionary(
                    self.current_device,
                    self.current_mode,
                    self.current_inherit,
                    self.button_array,
                )
        if self.using_inheritance:
            self.inherit_joystick_dictionary()

        self.filter_dictionary()
        return self.joystick_dictionary

    def filter_dictionary(self) -> dict:
        if isinstance(self.profiles, list) and len(self.profiles) > 0:
            for key, value in self.joystick_dictionary.items():
                for item in value.copy():
                    if not item in self.profiles:
                        self.joystick_dictionary[key].pop(item, None)
        return self.joystick_dictionary

    def get_devices(self):
        return self.file.getElementsByTagName("device")

    def get_mode_buttons(self):
        return self.mode.getElementsByTagName("button")

    def get_mode_hats(self):
        return self.mode.getElementsByTagName("hat")

    def get_device_modes(self):
        return self.device.getElementsByTagName("mode")

    def get_single_device(self):
        return self.device.getAttribute("name")

    def get_single_mode(self):
        return self.mode.getAttribute("name")

    def has_inheritance(self):
        inherit = self.mode.getAttribute("inherit")
        if inherit != "":
            if self.using_inheritance is not True:
                self.using_inheritance = True
            return inherit
        else:
            return False

    def inherited_modes(self):
        return self.mode.getAttribute("name")

    def extract_buttons(self):
        for i in self.buttons:
            if i.getAttribute("description") != "":
                self.button_array.update({"BUTTON_" + str(i.getAttribute("id")): str(i.getAttribute("description"))})
            else:
                self.button_array.update({"BUTTON_" + str(i.getAttribute("id")): self.no_bind_text})
        return self.button_array

    def extract_hats(self) -> None:
        for i in self.hats:
            hat_id = i.getAttribute("id")
            _logger.debug("Hat ID: {hat_id}")

            if i.getAttribute("description"):
                hat_description = i.getAttribute("description")
                _logger.debug("Hat has description: {hat_description}")
            else:
                hat_description = ""

            hat_containers = i.getElementsByTagName("container")

            if hat_containers:
                _logger.debug("Has containers: {hat_containers.length}")

                for container in hat_containers:
                    hat_positions = container.getElementsByTagName("action-set")
                    hat_count = hat_positions.length
                    increment = 8 / hat_count
                    pos = 1
                    _logger.debug(f"We have {hat_count} hat positions")

                    for position in hat_positions:
                        if position.getElementsByTagName("description"):
                            # Ignore more than 1 description. always use first
                            hat_direction_description = position.getElementsByTagName("description")[0].getAttribute(
                                "description"
                            )
                        else:
                            hat_direction_description = hat_description

                        _logger.debug(f"POV Position: {self.position_map[pos]}")

                        self.button_array.update(
                            {f"POV_{i.getAttribute('id')}_{self.position_map[pos]}": str(hat_direction_description)}
                        )

                        pos = pos + increment
            else:
                _logger.error(f"No container found for hat: {hat_id}")

    def get_device_count(self):
        return self.file.getElementsByTagName("device").length
