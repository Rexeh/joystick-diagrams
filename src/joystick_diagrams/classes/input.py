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


@dataclass
class Command:
    name: str


@dataclass
class Modifier:
    input: set
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
        if existing is None:
            _logger.warning(f"Modifier {modifier} for input {self.identifier} not found so adding")
            self.modifiers.append(Modifier(modifier, command))
        else:
            _logger.warning(f"Modifier {modifier} already exists for {self.identifier} and command has been overidden")
            existing.command = command

    def _check_existing_modifier(self, modifier: set) -> Modifier | None:
        for x in self.modifiers:
            if x.input == modifier:
                return x
        return None

    def __repr__(self):
        return f"Input: {self.identifier} {self.style} {self.command} {self.modifiers}"


class LogicalDevice:
    def __init__(self, guid: str):
        self.guid = guid
        self.inputs = []

    def create_input(self, input_id: str, style: InputTypes, command: Command, modifiers: list[Modifier]) -> None:
        existing = self.__check_existing_input(input_id, style)
        if not existing:
            self.inputs.append(Input(input_id, style, command, modifiers))
        else:
            _logger.warning(f"Input {input_id} already exists and will be overwritten")
            self.inputs[self.inputs.index(existing)].command = command

    def _get_input(self, input_id: str) -> Input | None:
        """
        Returns a specific input from stored inputs
        """
        for x in self.inputs:
            if x.identifier == input_id:
                return x
        return None

    def add_modifier_to_input(self, input_id, modifier: set, command: Command) -> None:
        """
        Adds a modifier to an input if it exists
        """
        obj = self._get_input(input_id)
        print(f"Object is: {obj}")
        if obj is None:
            # Add error handling for scenario where input does not exist
            return None
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


# What will consumers want to do?
# 1. Add a device
# - Not need to know or care that another class has instanciated it
# 2. Add an input to a device
# 3. Add a modifiers to a specific input


def clear_devices():
    """
    Clears all devices and inputs from the system.
    """
    _devices.clear()


def _get_devices() -> dict[str:LogicalDevice]:
    """Returns a dictionary of all devices"""
    return _devices


def _get_device(guid: str) -> LogicalDevice:
    return _devices[guid]


def add_device(guid: str) -> None:
    if guid not in _devices:
        _devices.update({guid: LogicalDevice(guid)})
    else:
        _logger.warning(f"Device {guid} already exists and will not be re-added")


def add_input_modifier(guid: str, input_id: str, modifier: set, command: Command) -> None:
    _get_device(guid).add_modifier_to_input(input_id, modifier, command)


def add_inputs(guid: str, **kwargs) -> None:
    _devices[guid].create_input(**kwargs)


add_device("92029209=09209202902")
add_device("92029209=09209202902")

add_inputs(
    "92029209=09209202902", input_id="button_a", style=InputTypes.BUTTON, command=Command("button_a"), modifiers=[]
)

add_input_modifier("92029209=09209202902", "button_a", {"ctrl", "alt"}, Command("button_1"))

add_inputs(
    "92029209=09209202902", input_id="button_a", style=InputTypes.BUTTON, command=Command("button_G"), modifiers=[]
)

print("-" * 20)
add_input_modifier("92029209=09209202902", "button_a", {"ctrl", "alt", "abc"}, Command("button_5"))
add_input_modifier("92029209=09209202902", "button_a", {"ctrl", "alt", "del"}, Command("button_2"))
