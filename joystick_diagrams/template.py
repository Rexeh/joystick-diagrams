"""Represents a Joystick Diagram template file format

Interacts with the template file to allow interogration of template configuration, and compatability with potential devices

"""

import logging
import re
from pathlib import Path

from joystick_diagrams.exceptions import JoystickDiagramsError

_logger = logging.getLogger(__name__)


class Template:
    BUTTON_KEY = re.compile(r"\bBUTTON_\d+\b", flags=re.IGNORECASE)
    MODIFIER_KEY = re.compile(r"\b[a-zA-Z]+_\d+_MOD_\d+", flags=re.IGNORECASE)
    HAT_KEY = re.compile(r"\bPOV_\d+_[URDL]+\b", flags=re.IGNORECASE)
    AXIS_KEY = re.compile(r"\bAXIS_[a-zA-Z]+_?\d?+\b", flags=re.IGNORECASE)
    TEMPLATE_NAMING_KEY = re.compile(r"\bTEMPLATE_NAME\b", flags=re.IGNORECASE)
    TEMPLATE_DATE_KEY = re.compile(r"\bCURRENT_DATE\b", flags=re.IGNORECASE)

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

    def get_template_mndifiers(self) -> set[str]:
        "Returns the available MODIFIER NUMBERS supported for a given CONTROL from the template"
        return {x.lower() for x in re.findall(self.MODIFIER_KEY, self.raw_data)}

    def get_template_hats(self) -> set[str]:
        "Returns the available HAT controls from the template"
        return {x.lower() for x in re.findall(self.HAT_KEY, self.raw_data)}

    def get_template_axis(self) -> set[str]:
        "Returns the available AXIS controls from the template"
        return {x.lower() for x in re.findall(self.AXIS_KEY, self.raw_data)}

    def get_template_buttons(self) -> set[str]:
        "Returns the available BUTTON controls from the template"
        return {x.lower() for x in re.findall(self.BUTTON_KEY, self.raw_data)}

    @property
    def template_name(self) -> bool:
        "Checks if the template supports naming"
        return bool(re.search(self.TEMPLATE_NAMING_KEY, self.raw_data))

    @property
    def date(self) -> bool:
        "Checks if the template supports dating"
        return bool(re.search(self.TEMPLATE_DATE_KEY, self.raw_data))

    @property
    def button_count(self) -> int:
        "Returns the number of buttons available"
        return len(self.get_template_buttons())

    @property
    def axis_count(self) -> int:
        "Returns the number of axis available"
        return len(self.get_template_axis())

    @property
    def hat_count(self) -> int:
        "Returns the number of hats available"
        return len(self.get_template_hats())

    @property
    def modifier_count(self) -> int:
        "Returns the number of modifiers available"
        return len(self.get_template_mndifiers())


if __name__ == "__main__":
    pass
