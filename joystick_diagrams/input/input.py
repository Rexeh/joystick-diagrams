"""
Joystick Diagrams Input Module

This module contains access to the creation and tracking of devices and their inputs

This module is designed to be used by Plugins, to share devices and inputs between them.

This module operates on FIFO basis, and is designed to be used by a single thread. Only one instance of a device can exist at a time.
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto

_logger = logging.getLogger(__name__)


@dataclass
class Modifier:
    modifiers: set[str]
    command: str


class Input_:
    def __init__(self, identifier: str, command: str) -> None:
        self.identifier = identifier.lower()
        self.command = command
        self.modifiers: list[Modifier] = []

    def add_modifier(self, modifier: set, command: str):
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
        _logger.debug(f"Existing modifiers: {self.modifiers}")
        for x in self.modifiers:
            _logger.debug(f"Checking for existing modifier {modifier} in {x}")
            if x.modifiers == modifier:
                _logger.debug(f"Modifier already  exists {x}")
                return x
        return None


if __name__ == "__main__":
    pass
