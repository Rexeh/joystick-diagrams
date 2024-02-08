"""Represents a Joystick Diagram template file format

Interacts with the template file to allow interogration of template configuration, and compatability with potential devices

"""

import logging
import re
from pathlib import Path

from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.input.device import Device_

_logger = logging.getLogger(__name__)


class Template:
    BUTTON_KEY = "BUTTON_\\d+"
    MODIFIER_KEY = "[a-zA-Z]+_\\d+_MOD_\\d+"
    HAT_KEY = "POV_\\d+_[URDL]+"
    AXIS_KEY = "AXIS_[a-zA-Z]+_?\\d?+"
    TEMPLATE_NAMING_KEY = "TEMPLATE_NAME"
    TEMPLATE_DATE_KEY = "CURRENT_DATE"

    def __init__(self, template_path: str):
        self.raw_data: str = self.get_template_data(Path(template_path))

    def get_template_data(self, template_path: Path):
        try:
            with Path(template_path).open("r", encoding="utf-8") as f:
                # TODO increased validation to check its a proper template file
                return f.read()
        except Exception as e:
            _logger.error(e)
            raise JoystickDiagramsError(
                "There was an issue reading the template file"
            ) from e

    def dry_run(self, device: Device_):
        """Computes mergeability of a Device to the Template.

        Returns list of missing controls from TEMPLATE
        """
        pass

    @property
    def modifiers(self) -> set[str]:
        "Returns the available MODIFIER NUMBERS supported for a given CONTROL from the template"
        return {
            x.lower()
            for x in re.findall(
                f"\\b{self.MODIFIER_KEY}", self.raw_data, flags=re.IGNORECASE
            )
        }

    @property
    def hats(self) -> set[str]:
        "Returns the available HAT controls from the template"
        return {
            x.lower()
            for x in re.findall(
                f"\\b{self.HAT_KEY}\\b", self.raw_data, flags=re.IGNORECASE
            )
        }

    @property
    def axis(self) -> set[str]:
        "Returns the available AXIS controls from the template"
        return {
            x.lower()
            for x in re.findall(
                f"\\b{self.AXIS_KEY}\\b", self.raw_data, flags=re.IGNORECASE
            )
        }

    @property
    def buttons(self) -> set[str]:
        "Returns the available BUTTON controls from the template"
        return {
            x.lower()
            for x in re.findall(
                f"\\b{self.BUTTON_KEY}\\b", self.raw_data, flags=re.IGNORECASE
            )
        }

    @property
    def template_name(self) -> bool:
        "Checks if the template supports naming"
        return bool(re.search(f"\\b{self.TEMPLATE_NAMING_KEY}\\b", self.raw_data))

    @property
    def date(self) -> bool:
        "Checks if the template supports dating"
        return bool(re.search(f"\\b{self.TEMPLATE_DATE_KEY}\\b", self.raw_data))

    @property
    def button_count(self) -> int:
        "Returns the number of buttons available"
        return len(self.buttons)

    @property
    def axis_count(self) -> int:
        "Returns the number of axis available"
        return len(self.axis)

    @property
    def hat_count(self) -> int:
        "Returns the number of hats available"
        return len(self.hats)

    @property
    def modifier_count(self) -> int:
        "Returns the number of modifiers available"
        return len(self.modifiers)


if __name__ == "__main__":
    pass
