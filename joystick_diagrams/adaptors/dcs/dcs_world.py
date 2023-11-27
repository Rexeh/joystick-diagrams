"""DCS World Lua Config Parser for use with Joystick Diagrams"""
import logging
import os
import re
from pathlib import Path

from ply import lex, yacc  # type: ignore

import joystick_diagrams.adaptors.dcs.dcs_world_lex  # pylint: disable=unused-import
import joystick_diagrams.adaptors.dcs.dcs_world_yacc  # pylint: disable=unused-import
import joystick_diagrams.adaptors.joystick_diagram_interface as jdi

_logger = logging.getLogger(__name__)

EASY_MODES = "_easy"


class DCSWorldParser(jdi.JDinterface):
    def __init__(self, path, easy_modes=True):
        jdi.JDinterface.__init__(self)
        self.path = path
        self.remove_easy_modes = easy_modes
        self.__easy_mode = EASY_MODES
        self.base_directory = self.__validate_base_directory()
        self.valid_profiles = self.__validate_profiles()
        self.joystick_listing = {}
        self.profiles_to_process = None
        self.profile_devices = None
        self.fq_path = None

    def __validate_base_directory(self) -> list:
        """validate the base directory structure, make sure there are files."""
        if "Config" in os.listdir(self.path):
            try:
                return os.listdir(os.path.join(self.path, "Config", "Input"))
            except FileNotFoundError:
                raise FileNotFoundError("DCS: No input directory found") from None
        else:
            raise FileNotFoundError("DCS: No Config Folder found in DCS Folder.")

    def __validate_profiles(self) -> list[str]:
        """
        Validate Profiles Routine
        """
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
        """
        Validate Inidividual Profile
        Return Valid Profile
        """

        if os.path.isdir(os.path.join(self.path, "Config", "Input", item)) and "joystick" in os.listdir(
            os.path.join(self.path, "Config", "Input", item)
        ):
            return os.listdir(os.path.join(self.path, "Config", "Input", item, "joystick"))

        return False

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

    def convert_button_format(self, button) -> str:
        """Convert DCS Buttons to match expected "BUTTON_X" format"""
        split = button.split("_")

        match len(split):
            case 2:
                if split[1][0:3] == "BTN":
                    return f"{split[1].replace('BTN', 'BUTTON_')}"
                elif split[1].isalpha():
                    return f"AXIS_{split[1]}"
                elif split[1][0:6] == "SLIDER":
                    return f"AXIS_SLIDER_{split[1][6:]}"
                else:
                    return f"{split[1]}"
            case 4:
                return f"{split[1].replace('BTN', 'POV')}_{split[2][3]}_{split[3]}"
            case _:
                _logger.warning(f"Button format not found for {split}")
                return f"{button}"

    def process_profiles(self, profile_list: list | None = None) -> dict:
        if isinstance(profile_list, list) and len(profile_list) > 0:
            self.profiles_to_process = profile_list
        else:
            self.profiles_to_process = self.get_validated_profiles()

        assert (
            len(self.profiles_to_process) != 0
        ), "DCS: There are no valid profiles to process"  ## Replace with exception type

        for profile in self.profiles_to_process:
            self.fq_path = os.path.join(self.path, "Config", "Input", profile, "joystick")
            self.profile_devices = os.listdir(os.path.join(self.fq_path))
            self.joystick_listing = {}
            for item in self.profile_devices:
                self.joystick_listing.update({item[:-48]: item})
            for joystick_device, joystick_file in self.joystick_listing.items():
                if os.path.isdir(os.path.join(self.fq_path, joystick_file)):
                    _logger.info("Skipping as Folder")
                else:
                    try:
                        _logger.debug(f"Obtaining file data  for {joystick_file}")
                        file_data = (
                            Path(os.path.join(self.fq_path, joystick_file))
                            .read_text(encoding="utf-8")
                            .replace("local diff = ", "")
                            .replace("return diff", "")
                        )

                    except FileNotFoundError as err:
                        _logger.error(
                            f"DCS: File {joystick_file} no longer found - \
                                It has been moved/deleted from directory. {err}"
                        )
                        raise

                    else:
                        parsed_config = self.parse_config(file_data)  ##Better handling - decompose

                        if parsed_config is None:
                            break

                        button_map = self.create_joystick_map(parsed_config)

                        self.update_joystick_dictionary(joystick_device, profile, False, button_map)
        return self.joystick_dictionary

    def parse_config(self, file: str):
        try:
            return self.parse_file(file)
        except Exception as error:
            _logger.error("There was a parsing issue with the text data, this could mean an unhandled character.")
            _logger.error(error)
            return None

    def create_joystick_map(self, data) -> dict:
        write_val = False
        button_array = {}

        if "keyDiffs" in data.keys():
            for value in data["keyDiffs"].values():
                for item, attribute in value.items():
                    if item == "name":
                        name = attribute
                    if item == "added":
                        button = self.convert_button_format(attribute[1]["key"])
                        write_val = True
                if write_val:
                    button_array.update({button: name})
                    write_val = False

        if "axisDiffs" in data.keys():
            for value in data["axisDiffs"].values():
                for item, attribute in value.items():
                    if item == "name":
                        name = attribute
                    if item in ["added", "changed"]:
                        axis = self.convert_button_format(attribute[1]["key"])
                        write_val = True
                if write_val:
                    button_array.update({axis: name})
                    write_val = False
        return button_array

    def parse_file(self, file: str) -> dict:
        # pylint: disable=unused-variable
        tokens = (
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

        t_LCURLY = r"\{"  # pylint: disable=invalid-name
        t_RCURLY = r"\}"  # pylint: disable=invalid-name
        t_LBRACE = r"\["  # pylint: disable=invalid-name
        t_RBRACE = r"\]"  # pylint: disable=invalid-name
        t_COMMA = r"\,"  # pylint: disable=invalid-name
        t_EQUALS = r"\="  # pylint: disable=invalid-name

        def t_DOUBLE_VAL(t):  # pylint: disable=invalid-name
            r"(\+|\-)?[0-9]+\.[0-9]+"
            t.value = float(t.value)
            return t

        def t_NUMBER(t):  # pylint: disable=invalid-name
            r"[0-9]+"
            t.value = int(t.value)
            return t

        def t_STRING(t):  # pylint: disable=invalid-name
            r"\"[\w|\/|\(|\)|\-|\:|\+|\,|\&|\.|\'|\<|\>|\s]+\" "
            t.value = t.value[1:-1]
            return t

        def t_TRUE(t):  # pylint: disable=invalid-name
            r"(true)"
            t.value = True
            return t

        def t_FALSE(t):  # pylint: disable=invalid-name
            r"(false)"
            t.value = False
            return t

        t_ignore = " \t\n"

        def t_error(t):  # pylint: disable=invalid-name
            _logger.error(f"Illegal character '{t.value[0]}'")
            t.lexer.skip(1)

        # Parsing rules

        def p_dict(t):  # pylint: disable=invalid-name
            """dict : LCURLY dvalues RCURLY"""
            t[0] = t[2]

        def p_dvalues(t):  # pylint: disable=invalid-name
            """dvalues : dvalue
            | dvalue COMMA
            | dvalue COMMA dvalues"""
            t[0] = t[1]
            if len(t) == 4:
                t[0].update(t[3])

        def p_key_expression(t):  # pylint: disable=invalid-name
            """key : LBRACE NUMBER RBRACE
            | LBRACE STRING RBRACE"""
            t[0] = t[2]

        def p_value_expression(t):  # pylint: disable=invalid-name
            """dvalue : key EQUALS STRING
            | key EQUALS boolean
            | key EQUALS DOUBLE_VAL
            | key EQUALS NUMBER
            | key EQUALS dict"""
            t[0] = {t[1]: t[3]}

        def p_boolean(p):  # pylint: disable=invalid-name
            """boolean : TRUE
            | FALSE
            """
            p[0] = p[1]

        def p_error(t):  # pylint: disable=invalid-name
            _logger.error(f"Syntax error at '{ (t.value)}'")

        # Build the lexer
        lexer = lex.lex(
            debug=False, optimize=1, lextab="dcs_world_lex", reflags=re.UNICODE | re.VERBOSE, errorlog=_logger
        )

        # Build the parser
        parser = yacc.yacc(debug=False, optimize=1, tabmodule="dcs_world_yacc", errorlog=_logger)

        # Parse the data
        try:
            data = parser.parse(file)
        except Exception as error:
            _logger.error(error)
            raise
        return data
