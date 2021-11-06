"""DCS World Lua Config Parser for use with Joystick Diagrams"""
import os
import re
from pathlib import Path
import ply.lex as lex
import ply.yacc as yacc
import joystick_diagrams.functions.helper as helper
import joystick_diagrams.adaptors.joystick_diagram_interface as jdi
import joystick_diagrams.adaptors.dcs_world_lex  # pylint: disable=unused-import
import joystick_diagrams.adaptors.dcs_world_parse  # pylint: disable=unused-import


class DCSWorldParser(jdi.JDinterface):
    def __init__(self, path, easy_modes=True):
        jdi.JDinterface.__init__(self)
        self.path = path
        self.remove_easy_modes = easy_modes
        self.__easy_mode = "_easy"
        self.base_directory = self.__validate_base_directory()
        self.valid_profiles = self.__validate_profiles()
        self.joystick_listing = {}
        self.file = None
        self.profiles_to_process = None
        self.profile_devices = None
        self.fq_path = None

    def __validate_base_directory(self):
        """validate the base directory structure, make sure there are files."""
        if "Config" in os.listdir(self.path):
            try:
                return os.listdir(os.path.join(self.path, "Config", "Input"))
            except FileNotFoundError:
                raise FileNotFoundError("DCS: No input directory found")
        else:
            raise FileNotFoundError("DCS: No Config Folder found in DCS Folder.")

    def __validate_profiles(self):
        """
        Validate Profiles Routine
        """
        if len(self.base_directory) > 0:
            valid_items = []
            for item in self.base_directory:
                valid = self.__validate_profile(item)
                if valid:
                    valid_items.append(item)
                else:
                    helper.log(
                        "DCS: Profile {} has no joystick directory files".format(item)
                    )
        else:
            raise FileExistsError("DCS: No profiles exist in Input directory!")

        return valid_items

    def __validate_profile(self, item):
        """
        Validate Inidividual Profile
        Return Valid Profile
        """

        if os.path.isdir(
            os.path.join(self.path, "Config", "Input", item)
        ) and "joystick" in os.listdir(
            os.path.join(self.path, "Config", "Input", item)
        ):
            return os.listdir(
                os.path.join(self.path, "Config", "Input", item, "joystick")
            )
        else:
            return False

    def get_validated_profiles(self):
        """ Expose Valid Profiles only to UI """
        if self.remove_easy_modes:
            return list(
                filter(
                    lambda x: False if self.__easy_mode in x else True,
                    self.valid_profiles,
                )
            )
        else:
            return self.valid_profiles

    def convert_button_format(self, button):
        """ Convert DCS Buttons to match expected "BUTTON_X" format """
        split = button.split("_")

        if len(split) == 2:
            if split[1][0:3] == "BTN":
                return split[1].replace("BTN", "BUTTON_")
            elif split[1].isalpha():
                return "AXIS_{}".format(split[1])
            elif split[1][0:6] == "SLIDER":
                return "AXIS_SLIDER_{}".format(split[1][6:])
            else:
                return split[1]

        elif len(split) == 4:
            return "{button}_{pov}_{dir}".format(
                button=split[1].replace("BTN", "POV"), pov=split[2][3], dir=split[3]
            )

    def process_profiles(self, profile_list=None):

        if isinstance(profile_list, list) and len(profile_list) > 0:
            self.profiles_to_process = profile_list
        else:
            self.profiles_to_process = self.get_validated_profiles()

        assert (
            len(self.profiles_to_process) != 0
        ), "DCS: There are no valid profiles to process"
        for profile in self.profiles_to_process:
            self.fq_path = os.path.join(
                self.path, "Config", "Input", profile, "joystick"
            )
            self.profile_devices = os.listdir(os.path.join(self.fq_path))
            self.joystick_listing = {}
            for item in self.profile_devices:
                self.joystick_listing.update({item[:-48]: item})
            for joystick_device, joystick_file in self.joystick_listing.items():

                if os.path.isdir(os.path.join(self.fq_path, joystick_file)):
                    print("Skipping as Folder")
                else:
                    try:
                        self.file = Path(
                            os.path.join(self.fq_path, joystick_file)
                        ).read_text(encoding="utf-8")
                        self.file = self.file.replace("local diff = ", "")  ## CLEAN UP
                        self.file = self.file.replace("return diff", "")  ## CLEAN UP
                    except FileNotFoundError:
                        raise FileExistsError(
                            "DCS: File {} no longer found - It has been moved/deleted from directory".format(
                                joystick_file
                            )
                        )
                    else:
                        dictionary_2 = self.parse_file()

                        button_map = self.create_joystick_map(dictionary_2)

                        self.update_joystick_dictionary(
                            joystick_device, profile, False, button_map
                        )
        return self.joystick_dictionary

    def create_joystick_map(self, data):
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

    def parse_file(self):
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
            r"\"[\w|\/|\(|\)|\-|\:|\+|\,|\&|\.|\'|\s]+\""
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
            print("Illegal character '%s'" % t.value[0])
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
            print("Syntax error at '%s'" % t.value)

        # Build the lexer
        lexer = lex.lex(
            debug=False,
            optimize=1,
            lextab="dcs_world_lex",
            reflags=re.UNICODE | re.VERBOSE,
        )

        # Build the parser
        parser = yacc.yacc(debug=False, optimize=1, tabmodule="dcs_world_parse")

        # Parse the data
        try:
            data = parser.parse(self.file)
        except Exception as error:
            helper.log(error, "error")
            raise "DCS Parser Exception"
        return data
