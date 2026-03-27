"""Joystick Gremlin (Version ~13) XML Parser for use with Joystick Diagrams.

Author: Robert Cox
"""
import logging
from pathlib import Path
from xml.dom import minidom

from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.input.axis import Axis, AxisDirection
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
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

AXIS_ID_MAP = {
    1: AxisDirection.X,
    2: AxisDirection.Y,
    3: AxisDirection.Z,
    4: AxisDirection.RX,
    5: AxisDirection.RY,
    6: AxisDirection.RZ,
    7: AxisDirection.SLIDER,
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

        # Track inheritance per (device_guid, mode_name) -> parent_mode_name
        # Inheritance is defined per-device in Joystick Gremlin XML
        inherit_map: dict[tuple[str, str], str] = {}

        for mode in modes:
            mode_name = mode.getAttribute("name")
            inherit = mode.getAttribute("inherit")

            # Create a profile for the mode using NAME
            _active_profile = profile_collection.create_profile(mode_name)

            # Create DEVICE from PARENT node
            _device_guid = mode.parentNode.getAttribute("device-guid")
            _device_name = mode.parentNode.getAttribute("name")

            if inherit:
                normalized_guid = Device_.validate_guid(_device_guid)
                inherit_map[(normalized_guid, mode_name.lower())] = inherit.lower()
            _device_obj = _active_profile.add_device(_device_guid, _device_name)

            # Process each binding element (axis/button/hat)
            for bind in mode.childNodes:
                if bind.nodeType == bind.ELEMENT_NODE:
                    self._process_bind(_device_obj, bind, _device_guid)

        # Resolve mode inheritance
        self._resolve_inheritance(profile_collection, inherit_map)

        return profile_collection

    def _process_bind(
        self, device_obj: Device_, bind: minidom.Element, device_guid: str
    ) -> None:
        """Process a single binding element (axis, button, or hat)."""
        bind_type = bind.tagName
        bind_description = bind.getAttribute("description")
        bind_identifier = int(bind.getAttribute("id"))

        match bind_type:
            case "axis":
                axis_direction = AXIS_ID_MAP.get(bind_identifier)
                if axis_direction and bind_description:
                    device_obj.create_input(Axis(axis_direction), bind_description)
                elif not axis_direction:
                    _logger.warning(
                        f"Unknown axis ID {bind_identifier} for device {device_guid}"
                    )
            case "button":
                if bind_description:
                    device_obj.create_input(Button(bind_identifier), bind_description)
            case "hat":
                for hat_control, hat_action in self.extract_hats(bind):
                    device_obj.create_input(hat_control, hat_action)
            case _:
                _logger.warning(
                    f"Unknown bind type ({bind_type}) detected while processing {device_guid}"
                )

    def _resolve_inheritance(
        self,
        profile_collection: ProfileCollection,
        inherit_map: dict[tuple[str, str], str],
    ) -> None:
        """Resolve mode inheritance per-device.

        Inheritance in Joystick Gremlin is per (device, mode) pair. For each
        inherited device-mode, parent bindings are added to the child where
        the child does not already have a binding for that input.
        """
        resolved: set[tuple[str, str]] = set()
        for key in inherit_map:
            self._resolve_device_inheritance(
                key, profile_collection, inherit_map, resolved
            )

    def _resolve_device_inheritance(
        self,
        key: tuple[str, str],
        profile_collection: ProfileCollection,
        inherit_map: dict[tuple[str, str], str],
        resolved: set[tuple[str, str]],
    ) -> None:
        """Resolve inheritance for a single (device_guid, mode_name) pair."""
        if key in resolved:
            return

        device_guid, child_mode = key
        parent_mode = inherit_map.get(key)
        if parent_mode is None or parent_mode == child_mode:
            if parent_mode == child_mode:
                _logger.warning(
                    f"Mode '{child_mode}' inherits from itself on device {device_guid}, skipping"
                )
            resolved.add(key)
            return

        # Resolve parent first if it also inherits on this device
        parent_key = (device_guid, parent_mode)
        if parent_key in inherit_map and parent_key not in resolved:
            self._resolve_device_inheritance(
                parent_key, profile_collection, inherit_map, resolved
            )

        self._merge_parent_into_child(
            profile_collection, device_guid, parent_mode, child_mode
        )
        resolved.add(key)

    def _merge_parent_into_child(
        self,
        profile_collection: ProfileCollection,
        device_guid: str,
        parent_mode: str,
        child_mode: str,
    ) -> None:
        """Copy parent device inputs into child device where child has no binding."""
        parent_profile = profile_collection.get_profile(parent_mode)
        child_profile = profile_collection.get_profile(child_mode)

        if not parent_profile or not child_profile:
            return

        parent_device = parent_profile.get_device(device_guid)
        if not parent_device:
            return

        child_device = child_profile.get_device(device_guid)
        if not child_device:
            child_device = child_profile.add_device(device_guid, parent_device.name)

        for input_type, inputs in parent_device.get_inputs().items():
            for input_key, input_obj in inputs.items():
                if child_device.get_input(input_type, input_key) is None:
                    child_device.create_input(
                        input_obj.input_control, input_obj.command
                    )

        _logger.debug(
            f"Inherited '{parent_mode}' into '{child_mode}' for device {device_guid}"
        )

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
            hat_mappings = self.handle_hat_button_container(
                hat_id, filtered_hat_containers
            )

        if basic_containers:
            hat_mappings = self.handle_virtual_button_container(hat_id, hat_containers)

        return hat_mappings

    def handle_virtual_button_container(
        self, hat_id, containers: minidom.NodeList[minidom.Element]
    ):
        hat_mappings = []
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
                print("No point continuing")
                continue

            virtual_buttons: minidom.Element = container.getElementsByTagName(
                "virtual-button"
            )

            if not virtual_buttons:
                # If we don't have virtual buttons we have no hats to process
                continue

            if len(virtual_buttons) != 1:
                print("Not expected number of virtual button elements")
                continue

            attributes = [x for x in virtual_buttons[0].attributes.keys()]

            for attribute in attributes:
                hat_mappings.append(
                    (
                        Hat(hat_id, HatDirection[VIRTUAL_HAT_POSITIONS[attribute]]),
                        container_description,
                    )
                )

        return hat_mappings

    def handle_hat_button_container(
        self, hat_id, hat_containers: minidom.NodeList[minidom.Element]
    ):
        four_way_hat = 4

        for container in hat_containers:
            button_count = int(container.getAttribute("button-count"))

            hat_positions = container.getElementsByTagName("action-set")

            hat_mappings = []

            # Iterate each ACTION_SET, for the HAT_BUTTONS
            for hat_direction_no, position in enumerate(hat_positions, 1):
                # Get the description node if exists
                hat_description_node = position.getElementsByTagName("description")

                hat_direction = hat_direction_no

                if button_count == four_way_hat:
                    hat_direction = hat_direction_no + (hat_direction_no - 1)

                # If no node then continue
                if not hat_description_node:
                    continue

                # What if multiple hat_description_nodes

                hat_description = hat_description_node[0].getAttribute("description")

                if not hat_description:
                    # If we don't have a description then no point using the item
                    continue

                hat_position_to_string = HAT_POSITIONS[hat_direction]
                hat_mappings.append(
                    (Hat(hat_id, HatDirection[hat_position_to_string]), hat_description)
                )

        return hat_mappings
