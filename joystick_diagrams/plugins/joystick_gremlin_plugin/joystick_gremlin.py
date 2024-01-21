"""Joystick Gremlin (Version ~13) XML Parser for use with Joystick Diagrams.

Author: Robert Cox
"""
import logging
from typing import Union
from xml.dom import minidom

from joystick_diagrams.input.profile_collection import ProfileCollection

_logger = logging.getLogger(__name__)

HAT_POSITIONS = {
    1: "U",
    2: "UR",
    3: "R",
    4: "DR",
    5: "D",
    6: "DL",
    7: "L",
    8: "UL",
}


class JoystickGremlinParser:
    def __init__(self, filepath):
        self.file = self.parse_xml_file(filepath)

    def parse_xml_file(self, xml_file) -> minidom.Document:
        ## Improve loading of file, checks for validity etc
        return minidom.parse(xml_file)

    def create_dictionary(self) -> ProfileCollection:
        profile_collection = ProfileCollection()

        # Get all the modes
        modes = self.file.getElementsByTagName("mode")

        for mode in modes:
            # Create a profile for the mode using NAME
            _active_profile = profile_collection.create_profile(mode.getAttribute("name"))

            # Create DEVICE from PARENT node
            _device_guid = mode.parentNode.getAttribute("device-guid")
            _device_name = mode.parentNode.getAttribute("name")
            _device_obj = _active_profile.add_device(_device_guid, _device_name)

            # Iterate each AXIS / Button
            bindings = mode.childNodes

            for bind in bindings:
                if bind.nodeType == bind.ELEMENT_NODE:
                    bind_type = bind.tagName
                    bind_description = bind.getAttribute("description")
                    bind_identifier = bind.getAttribute("id")

                    match bind_type:
                        case "axis":
                            if bind_description:
                                _device_obj.create_input(bind_identifier, bind_description)
                        case "button":
                            if bind_description:
                                _device_obj.create_input(bind_identifier, bind_description)
                        case "hat":
                            hats = self.extract_hats(bind)

                            if hats:
                                for hat_id, hat_action in hats:
                                    _device_obj.create_input(hat_id, hat_action)
                        case _:
                            _logger.warning("Unknown bind type ({bind_type}) detected while processing {_device_guid}")

        return profile_collection

    def extract_hats(self, hat_node) -> list[Union[str, str] | None]:
        """Extract the hat positions for a given HAT node.

        Each HAT node may contain a CONTAINER, which may contain N number of action-set nodes

        Returns array of arrays containing the formatted POV CONTROL and ACTION

        """
        hat_id: str = hat_node.getAttribute("id")
        hat_description: str = hat_node.getAttribute("description") or ""
        hat_mappings: list = []

        _logger.debug("Hat ID: {hat_id}")
        _logger.debug("Hat has description: {hat_description}")

        # Get the containers
        hat_container = hat_node.getElementsByTagName("container")

        if not hat_container:
            return hat_mappings

        _logger.debug("Has containers: {hat_containers.length}")

        hat_positions = hat_container[0].getElementsByTagName("action-set")

        hat_mappings = []

        for position in hat_positions:
            # Get REMAP of node (assumes 1)
            hat_position_id = position.getElementsByTagName("remap")[0].getAttribute("button")

            # Get the description node if exists
            hat_description_check = position.getElementsByTagName("description")

            # If no node then continue
            if not hat_description_check:
                continue

            hat_description = hat_description_check[0].getAttribute("description")

            if not hat_description:
                # If we don't have a description then no point using the item
                continue

            hat_mappings.append([f"POV_{hat_id}_{HAT_POSITIONS[int(hat_position_id)]}", hat_description])

        return hat_mappings


if __name__ == "__main__":
    pass
