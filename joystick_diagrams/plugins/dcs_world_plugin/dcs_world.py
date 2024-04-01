"""DCS World Lua Config Parser for use with Joystick Diagrams"""

import logging
import os
import re
from pathlib import Path

from ply import lex, yacc

from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.input.axis import Axis, AxisDirection, AxisSlider
from joystick_diagrams.input.button import Button  # type: ignore

#################
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.hat import Hat, HatDirection
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.input.profile_collection import ProfileCollection

_logger = logging.getLogger(__name__)

EASY_MODES = "_easy"
CONFIG_DIR = "Config"
INPUT_DIR = "Input"
JOYSTICK_DIR = "joystick"


GUID_POSITION_SLICE = slice(-46, -10)
NAME_POSITION_SLICE = slice(-48)


class DCSWorldParser:
    def __init__(self, path, easy_modes=True):
        self.path = Path(path)
        self.remove_easy_modes = easy_modes
        self.__easy_mode = EASY_MODES
        self.base_directory = self.__validate_base_directory()
        self.valid_profiles = self.__validate_profiles()
        self.joystick_listing = {}
        self.profiles_to_process = None
        self.profile_devices = None
        self.fq_path = None

    def __validate_base_directory(self) -> list:
        """Validate the base directory structure, make sure there are files."""
        # TODO refactor
        if CONFIG_DIR in os.listdir(self.path):
            try:
                return os.listdir(os.path.join(self.path, CONFIG_DIR, INPUT_DIR))
            except FileNotFoundError:
                raise FileNotFoundError("DCS: No input directory found") from None
        else:
            raise FileNotFoundError("DCS: No Config Folder found in DCS Folder.")

    def __validate_profiles(self) -> list[str]:
        """Validate Profiles Routine"""
        if len(self.base_directory) == 0:
            raise FileExistsError("DCS: No profiles exist in Input directory!")

        valid_items = []
        for item in self.base_directory:
            valid = self.__validate_profile(item)
            if valid:
                valid_items.append(item)
            else:
                _logger.info(f"DCS: Profile {item} has no joystick directory files")

        return valid_items

    def __validate_profile(self, item: str) -> list | bool:
        """Validate Inidividual Profile
        Return Valid Profile
        """

        item_path = Path.joinpath(self.path, CONFIG_DIR, INPUT_DIR, Path(item))

        if not item_path.is_dir():
            return False

        if not {x for x in item_path.iterdir() if x.stem == JOYSTICK_DIR}:
            return False

        item_joystick_files_directory = Path.joinpath(item_path, JOYSTICK_DIR)
        valid_files = self.get_valid_files_for_profile(item_joystick_files_directory)

        if valid_files:
            return valid_files

        return False

    def get_valid_files_for_profile(self, path: Path) -> list[Path]:
        """Returns a list of files deemed to be valid in a DCS Profile device type directory"""
        return list(
            filter(
                lambda x: x.suffix == ".lua" and not x.is_dir(),
                path.iterdir(),
            )
        )

    def get_validated_profiles(self) -> list[str]:
        """Expose Valid Profiles only to UI"""
        if self.remove_easy_modes:
            return list(
                filter(
                    lambda x: False if self.__easy_mode in x else True,
                    self.valid_profiles,
                )
            )
        return self.valid_profiles

    def convert_button_format(
        self, button: str
    ) -> Axis | Hat | Button | AxisSlider | None:
        """Convert DCS Buttons to match expected "BUTTON_X" format"""
        split: list = button.split("_")
        _logger.debug(f"Converting button {button}")
        match len(split):
            case 2:
                if split[1][0:3] == "BTN":
                    # Standard Button
                    button_number: int = int(split[1][3:])
                    _logger.debug(f"Parsing button {button_number}")
                    return Button(button_number)
                elif split[1].isalpha():
                    # Standard Axis
                    axis_id: str = split[1]
                    _logger.debug(f"Parsing AXIS {axis_id}")
                    return Axis(AxisDirection[axis_id])
                elif split[1][0:6] == "SLIDER":
                    # Slider Axis
                    slider_id: int = int(split[1][6:])
                    _logger.debug(f"Parsing Slider Axis {slider_id}")
                    return AxisSlider(slider_id)
            case 4:
                # POV Slider control
                pov_id: int = int(split[2][3])
                pov_direction: str = split[3]
                _logger.debug(f"Parsing Hat ID {pov_id} direction {pov_direction}")
                return Hat(pov_id, HatDirection[pov_direction])
            case _:
                _logger.warning(f"Button format not found for {split}")

        return None

    def process_profiles(self, profile_list: list | None = None) -> ProfileCollection:
        if isinstance(profile_list, list) and len(profile_list) > 0:
            self.profiles_to_process = profile_list
        else:
            self.profiles_to_process = self.get_validated_profiles()

        collection = ProfileCollection()

        if len(self.profiles_to_process) == 0:
            _logger.warning("No profiles were found, so nothing to process.")
            return collection

        _logger.info(f"Profiles to be processed {self.profiles_to_process}")
        for profile in self.profiles_to_process:
            _logger.debug(f"Processing {profile=}")
            profile_object = collection.create_profile(profile_name=profile)
            self.fq_path = os.path.join(
                self.path, CONFIG_DIR, INPUT_DIR, profile, JOYSTICK_DIR
            )
            self.profile_devices = self.get_valid_files_for_profile(Path(self.fq_path))

            for item in self.profile_devices:
                self.process_profile_device(item, profile_object)

        return collection

    def process_profile_device(self, item: Path, profile: Profile_):
        _logger.debug(f"Processing {profile=} device {item=}")
        guid, name = (
            item.name[GUID_POSITION_SLICE],
            item.name[NAME_POSITION_SLICE],
        )

        # Handle lua files without a valid GUID  > TODO push into validate_files?
        try:
            Device_.validate_guid(guid)
        except ValueError as e:
            _logger.error(e)
            return

        active_profile = profile.add_device(guid, name)

        try:
            _logger.debug(f"Obtaining file data  for {item}")
            file_data = (
                item.read_text(encoding="utf-8")
                .replace("local diff = ", "")
                .replace("return diff", "")
            )

        except FileNotFoundError as err:
            _logger.error(
                f"DCS: File {item} no longer found - \
                    It has been moved/deleted from directory. {err}"
            )
            raise JoystickDiagramsError(err) from err

        else:
            parsed_config = self.parse_config(file_data)  ##Better handling - decompose

            if parsed_config is None:
                _logger.debug(f"Parsing failed for {item}")
                return

            self.assign_to_inputs(parsed_config, active_profile)

    def assign_to_inputs(self, config: dict, profile: Device_):
        search_keys = ["keyDiffs", "axisDiffs"]

        for key in search_keys:
            if key in config.keys():
                for data in config[key].values():
                    operation = data["name"]
                    _logger.debug(f"Operation name is currently {operation=}")
                    if data.get("added"):
                        for binding in data["added"].values():
                            input_identifier = self.convert_button_format(
                                binding["key"]
                            )

                            if not input_identifier:
                                continue

                            # Create Reforms first
                            if binding.get("reformers"):
                                # Initialise base button if not exists

                                reform_set = self.reformers_to_set(
                                    binding.get("reformers")
                                )

                                _logger.debug(
                                    f"Modifiers {reform_set=} and type is {type(reform_set)}"
                                )

                                profile.add_modifier_to_input(
                                    input_identifier, reform_set, operation
                                )
                            else:
                                profile.create_input(input_identifier, operation)

    def reformers_to_set(self, reformers: dict) -> set:
        return {x for x in reformers.values()}

    def parse_config(self, file: str) -> dict | None:
        try:
            return self.parse_file(file)
        except Exception as error:
            _logger.error(
                "There was a parsing issue with the text data, this could mean an unhandled character."
            )
            _logger.error(error)
            return None

    def parse_file(self, file: str) -> dict:  # noqa
        # Linter disabled for this function, this is the format required by PLY

        tokens = (  # noqa
            "LCURLY",
            "RCURLY",
            "STRING",
            "NUMBER",
            "LBRACE",
            "RBRACE",
            "COMMA",
            "EQUALS",
            "TRUE",
            "FALSE",
            "DOUBLE_VAL",
        )

        t_LCURLY = r"\{"  # noqa
        t_RCURLY = r"\}"  # noqa
        t_LBRACE = r"\["  # noqa
        t_RBRACE = r"\]"  # noqa
        t_COMMA = r"\,"  # noqa
        t_EQUALS = r"\="  # noqa

        def t_DOUBLE_VAL(t):  # noqa
            r"(\+|\-)?[0-9]+\.[0-9]+"
            t.value = float(t.value)
            return t

        def t_NUMBER(t):  # noqa
            r"[0-9]+"
            t.value = int(t.value)
            return t

        def t_STRING(t):  # noqa
            r"\"([^\"\\]|\\.)*\" "
            t.value = t.value[1:-1]
            return t

        def t_TRUE(t):  # noqa
            r"(true)"
            t.value = True
            return t

        def t_FALSE(t):  # noqa
            r"(false)"
            t.value = False
            return t

        t_ignore = " \t\n"  # noqa

        def t_error(t):  # noqa
            _logger.error(f"Illegal character '{t.value[0]}'")
            t.lexer.skip(1)

        # Parsing rules

        def p_dict(t):  # noqa
            """Dict : LCURLY dvalues RCURLY"""
            t[0] = t[2]

        def p_dvalues(t):  # noqa
            """Dvalues : dvalue
            | dvalue COMMA
            | dvalue COMMA dvalues
            """
            t[0] = t[1]
            if len(t) == 4:  # noqa
                t[0].update(t[3])

        def p_key_expression(t):  # noqa
            """Key : LBRACE NUMBER RBRACE
            | LBRACE STRING RBRACE
            """
            t[0] = t[2]

        def p_value_expression(t):  # noqa
            """Dvalue : key EQUALS STRING
            | key EQUALS boolean
            | key EQUALS DOUBLE_VAL
            | key EQUALS NUMBER
            | key EQUALS dict
            """
            t[0] = {t[1]: t[3]}

        def p_boolean(p):  # noqa
            """Boolean : TRUE
            | FALSE
            """
            p[0] = p[1]

        def p_error(t):  # noqa
            _logger.error(f"Syntax error at '{ (t.value)}'")

        # Build the lexer
        lex.lex(
            debug=False,
            optimize=1,
            lextab="lextab",
            reflags=re.UNICODE | re.VERBOSE,
            errorlog=_logger,
        )  # noqa

        # Build the parser
        parser = yacc.yacc(
            debug=False, optimize=1, tabmodule="dcs_world_yacc", errorlog=_logger
        )

        # Parse the data
        try:
            data = parser.parse(file)
        except Exception as error:
            _logger.error(error)
            raise
        return data


if __name__ == "__main__":
    pass
