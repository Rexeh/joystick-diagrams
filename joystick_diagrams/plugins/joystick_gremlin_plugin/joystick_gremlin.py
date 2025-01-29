"""Joystick Gremlin (Version ~13) XML Parser for use with Joystick Diagrams.

Author: Robert Cox
"""
import logging
from pathlib import Path
from xml.dom import minidom

from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.axis import Axis, AxisDirection
from joystick_diagrams.input.hat import Hat, HatDirection
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

VIRTUAL_HAT_POSITIONS = {
    "north": HAT_POSITIONS[1],
    "north-east": HAT_POSITIONS[2],
    "east": HAT_POSITIONS[3],
    "south-east": HAT_POSITIONS[4],
    "south": HAT_POSITIONS[5],
    "south-west": HAT_POSITIONS[6],
    "west": HAT_POSITIONS[7],
    "north-west": HAT_POSITIONS[8],
}


class JoystickGremlinParser:
    def __init__(self, filepath: Path):
        import os

        _logger.debug(os.access(Path(filepath), os.R_OK))
        self.file = self.parse_xml_file(Path(filepath))

    def parse_xml_file(self, xml_file: Path) -> minidom.Document:
        parsed_xml = minidom.parse(str(xml_file))
        valid = self.validate_xml(parsed_xml)

        if valid:
            return parsed_xml

        raise JoystickDiagramsError("File was not a valid Joystick Gremlin XML")

    def validate_xml(self, data: minidom.Document) -> bool:
        """Very basic check for validity"""
        if len(data.getElementsByTagName("mode")) > 0:
            return True
        else:
            return False

    def create_dictionary(self) -> ProfileCollection:
        """Creates a valid ProfileCollection from Joystick Gremlin XML

        Returns ProfileCollection
        """
        profile_collection = ProfileCollection()

        # Get all the modes
        modes = self.file.getElementsByTagName("mode")

        for mode in modes:
            # Create a profile for the mode using NAME
            _active_profile = profile_collection.create_profile(
                mode.getAttribute("name")
            )

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
                    bind_identifier = int(bind.getAttribute("id"))

                    match bind_type:
                        case "axis":
                            if bind_description:
                                _device_obj.create_input(
                                    Axis(self.map_axis(bind_identifier)), bind_description
                                )
                        case "button":
                            if bind_description:
                                _device_obj.create_input(
                                    Button(bind_identifier), bind_description
                                )
                        case "hat":
                            hats = self.extract_hats(bind)

                            if hats:
                                for hat_control, hat_action in hats:
                                    _device_obj.create_input(hat_control, hat_action)
                        case _:
                            _logger.warning(
                                f"Unknown bind type ({bind_type}) detected while processing {_device_guid}"
                            )

        return profile_collection

    def map_axis(self, id):
        match id:
            case 1:
                return AxisDirection.X
            case 2:
                return AxisDirection.Y
            case 3:
                return AxisDirection.Z
            case 4:
                return AxisDirection.RX
            case 5:
                return AxisDirection.RY
            case 6:
                return AxisDirection.RZ
            case 7:
                return AxisDirection.SLIDER


    def extract_hats(self, hat_node: minidom.Element) -> list[tuple[Hat, str]]:
        """Extract the hat positions for a given HAT node.

        Each HAT node may contain a CONTAINER, which may contain N number of action-set nodes

        Returns array of arrays containing the HAT CONTROL and ACTION

        """
        hat_id: int = int(hat_node.getAttribute("id"))
        hat_description: str = hat_node.getAttribute("description") or ""
        hat_mappings: list = []

        _logger.debug(f"Hat ID: {hat_id}")
        _logger.debug(f"Hat has description: {hat_description}")

        # Get the containers
        hat_containers = hat_node.getElementsByTagName("container")

        if not hat_containers:
            return hat_mappings

        # Gather container types
        basic_containers = [
            x for x in hat_containers if x.getAttribute("type") == "basic"
        ]
        filtered_hat_containers = [
            x for x in hat_containers if x.getAttribute("type") == "hat_buttons"
        ]

        _logger.debug(f"Basic Containers: {len(basic_containers)}")
        _logger.debug(f"Hat Containers: {len(filtered_hat_containers)}")

        if filtered_hat_containers:
            self.handle_hat_button_container(
                hat_id, filtered_hat_containers, hat_mappings
            )

        if basic_containers:
            self.handle_virtual_button_container(
                hat_id, hat_containers, hat_mappings
            )

        _logger.debug(f"Hat Mappings: {hat_mappings}")
        return hat_mappings

    def handle_virtual_button_container(
        self, hat_id, containers: minidom.NodeList[minidom.Element], hat_mappings
    ):
        for container in containers:
            # Check if we have a top level description
            container_description = (
                container.getAttribute("description")
                if container.getAttribute("description") != ""
                else None
            )

            # Try source description from inner block
            if not container_description:
                container_description = " - ".join(
                    {
                        x.getAttribute("description")
                        for x in container.getElementsByTagName("description")
                    }
                )

            # Skip processing if we have no descriptions
            if not container_description:
                _logger.debug(f"No point continuing")
                continue

            virtual_buttons: minidom.Element = container.getElementsByTagName(
                "virtual-button"
            )

            if not virtual_buttons:
                # If we don't have virtual buttons we have no hats to process
                continue

            if len(virtual_buttons) != 1:
                _logger.debug(f"Not expected number of virtual button elements")
                continue

            attributes = [x for x in virtual_buttons[0].attributes.keys()]

            for attribute in attributes:
                hat_mappings.append(
                    (
                        Hat(hat_id, HatDirection[VIRTUAL_HAT_POSITIONS[attribute]]),
                        container_description,
                    )
                )
        _logger.debug(f"Hat Mappings from Virtual Button: {hat_mappings}")

    def handle_hat_button_container(
        self, hat_id, hat_containers: minidom.NodeList[minidom.Element], hat_mappings
    ):
        four_way_hat = 4

        for container in hat_containers:
            button_count = int(container.getAttribute("button-count"))

            hat_positions = container.getElementsByTagName("action-set")

            _logger.debug(f"Hat Positions: {hat_positions}")

            # Iterate each ACTION_SET, for the HAT_BUTTONS
            for hat_direction_no, position in enumerate(hat_positions, 1):
                # Get the description node if exists
                hat_description_node = position.getElementsByTagName("description")

                _logger.debug(f"Hat Description Node: {hat_description_node}")
                hat_direction = hat_direction_no

                if button_count == four_way_hat:
                    hat_direction = hat_direction_no + (hat_direction_no - 1)

                # If no node then continue
                if not hat_description_node:
                    continue

                # What if multiple hat_description_nodes

                hat_description = hat_description_node[0].getAttribute("description")
                _logger.debug(f"Hat Description: {hat_description}")

                if not hat_description:
                    # If we don't have a description then no point using the item
                    continue

                hat_position_to_string = HAT_POSITIONS[hat_direction]
                hat_mappings.append(
                    (Hat(hat_id, HatDirection[hat_position_to_string]), hat_description)
                )

        _logger.debug(f"Hat Mappings from Hat Button Container: {hat_mappings}")


if __name__ == "__main__":
    pars = JoystickGremlinParser(
        Path(
            r"D:\Git Repos\joystick-diagrams\tests\data\joystick_gremlin\gremlin_pov_container_hat_buttons.xml"
        )
    )
    # pars = JoystickGremlinParser(
    #     Path(
    #         r"D:\Git Repos\joystick-diagrams\tests\data\joystick_gremlin\gremlin_hat_virtual_buttons.xml"
    #     )
    # )

    _logger.setLevel(logging.DEBUG)
    data = pars.create_dictionary()
    print(data)
