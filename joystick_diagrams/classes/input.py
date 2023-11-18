"""
Joystick Diagrams Input Module

This module contains access to the creation and tracking of devices and their inputs

This module is designed to be used by Plugins, to share devices and inputs between them.

This module operates on FIFO basis, and is designed to be used by a single thread. Only one instance of a device can exist at a time.
"""

from dataclasses import dataclass
from enum import auto, Enum
import logging

_logger = logging.getLogger(__name__)
_devices = {}

print(__name__)


@dataclass
class Command:
    name: str


@dataclass
class Modifier:
    modifiers: set
    command: Command


class InputTypes(Enum):
    BUTTON = auto()
    AXIS = auto()

    @staticmethod
    def validate(identifier):
        return "baaa"


class Input:
    def __init__(self, identifier: str, style: InputTypes, command: Command, modifiers: list[Modifier] = None) -> None:
        style.validate(identifier)
        self.identifier = identifier
        self.style = style
        self.command = command
        self.modifiers = modifiers = [] if modifiers is None else modifiers

    def add_modifier(self, modifier: set, command: Command):
        """
        Adds a modifier to an existing input, or amends an existing modifier
        """
        existing = self._check_existing_modifier(modifier)

        _logger.info(f"Existing modifier check is {existing}")

        if existing is None:
            _logger.info(f"Modifier {modifier} for input {self.identifier} not found so adding")
            self.modifiers.append(Modifier(modifier, command))
        else:
            _logger.info(f"Modifier {modifier} already exists for {self.identifier} and command has been overidden")
            existing.command = command

    def _check_existing_modifier(self, modifier: set) -> Modifier | None:
        _logger.debug(f"Checking for existing modifier {modifier}")
        _logger.debug(f"Existing modifiers: {self.modifiers}")

        for x in self.modifiers:
            if x.modifiers == modifier:
                return x
        return None


class LogicalDevice:
    def __init__(self, guid: str, name: str):
        self.guid = guid.strip().lower()
        self.name = name.strip().lower()
        self.inputs = []

    def create_input(self, input_id: str, style: InputTypes, command: Command) -> None:
        existing = self.__check_existing_input(input_id, style)
        if not existing:
            self.inputs.append(Input(input_id, style, command))
        else:
            _logger.debug(f"Input {input_id} already exists and will be overwritten")
            self.inputs[self.inputs.index(existing)].command = command

    def _get_input(self, input_id: str) -> Input | None:
        """
        Returns a specific input from stored inputs
        """
        for x in self.inputs:
            if x.identifier == input_id:
                return x
        return None

    def get_device_inputs(self) -> dict:
        return self.inputs

    def add_modifier_to_input(self, input_id, modifier: set, command: Command) -> None:
        """
        Adds a modifier to an input if it exists
        """

        _logger.debug(f"Adding modifier {modifier} to input {input_id}")
        obj = self._get_input(input_id)
        _logger.debug(f"Modifier input is: {obj}")
        if obj is None:
            self.create_input(input_id, InputTypes.BUTTON, "Not Used")
            obj = self._get_input(input_id)
            _logger.debug(f"Modifier input created now: {obj}")
        obj.add_modifier(modifier, command)

    def __check_existing_input(self, input_id: str, style: InputTypes) -> Input | None:
        """
        One instance of an input can exist, based on the input ID and style

        Returns Input or None
        """
        for x in self.inputs:
            if x.identifier == input_id and x.style == style:
                return x
        return None


def clear_devices():
    """
    Clears all devices and inputs from the system.
    """
    _devices.clear()


def get_devices(guid=None) -> dict[str:LogicalDevice]:
    """Returns a dictionary of all devices"""
    return _get_device(guid) if guid else _devices


def _get_device(guid: str) -> LogicalDevice:
    return _devices[guid]


def add_device(guid: str, name: str) -> LogicalDevice:
    if guid not in _devices:
        _devices.update({guid: LogicalDevice(guid, name)})
    else:
        _logger.warning(f"Device {guid} already exists and will not be re-added")

    return _devices[guid]


def add_input_modifier(guid: str, input_id: str, modifier: set, command: Command) -> None:
    _get_device(guid).add_modifier_to_input(input_id, modifier, command)


def add_inputs(guid: str, **kwargs) -> None:
    _devices[guid].create_input(**kwargs)
