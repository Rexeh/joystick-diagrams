'''DCS World Lua Config Parser for use with Joystick Diagrams'''
import os
import re
from pathlib import Path
import ply.lex as lex
import ply.yacc as yacc
import functions.helper as helper
import adaptors.joystick_diagram_interface as jdi
import adaptors.dcs_world_lex # Do not remove - PLY production requirement
import adaptors.dcs_world_parse # Do not remove - PLY production requirement

class DCSWorld_Parser(jdi.JDinterface):

    def __init__(self, path, easy_modes=True):
        jdi.JDinterface.__init__(self)
        self.path = path
        self.remove_easy_modes = easy_modes
        self.__easy_mode = '_easy'
        self.base_directory = self.__validateBaseDirectory()
        self.valid_profiles = self.__validateProfiles()
        self.joystick_listing = {}

    def __validateBaseDirectory(self):
        '''validate the base directory structure, make sure there are files.'''
        if 'Config' in os.listdir(self.path):
            try:
                return os.listdir(os.path.join(self.path, 'Config', 'Input'))
            except FileNotFoundError:
                raise FileNotFoundError("DCS: No input directory found")
        else:
            raise FileNotFoundError("DCS: No Config Folder found in DCS Folder.")
 
    def __validateProfiles(self):
        '''
        Validate Profiles Routine
        '''
        if len(self.base_directory)>0:
            valid_items = []
            for item in self.base_directory:
                valid = self.__validateProfile(item)
                if valid:
                    valid_items.append(item)
                else:
                    helper.log("DCS: Profile {} has no joystick directory files".format(item))
        else:
            raise FileExistsError("DCS: No profiles exist in Input directory!")

        return valid_items

    def __validateProfile(self, item):
        '''
        Validate Inidividual Profile
        Return Valid Profile
        '''
        #TODO add additional checking for rogue dirs/no files etc
        
        if os.path.isdir(os.path.join(self.path, 'Config', 'Input', item)) and 'joystick' in os.listdir(os.path.join(self.path, 'Config', 'Input', item)):
            return os.listdir(os.path.join(self.path, 'Config', 'Input', item, 'joystick'))
        else:
            return False

    def getValidatedProfiles(self):
        ''' Expose Valid Profiles only to UI '''
        if self.remove_easy_modes:
                return list(filter(lambda x: False if self.__easy_mode in x else True, self.valid_profiles))
        else:
            return self.valid_profiles

    def convert_button_format(self, button):
        ''' Convert DCS Buttons to match expected "BUTTON_X" format '''
        new = button.split('_')[1]
        rep = new.replace("BTN", "BUTTON_")
        return rep

    def processProfiles(self, profile_list=[]):
        if len(profile_list)>0:
            self.profiles_to_process = profile_list
        else:
            self.profiles_to_process = self.getValidatedProfiles()

        assert len(self.profiles_to_process) != 0, "DCS: There are no valid profiles to process"
        for profile in self.profiles_to_process:
            self.fq_path = os.path.join(self.path,'Config', 'Input', profile,'joystick')
            self.profile_devices = os.listdir(os.path.join(self.fq_path))
            self.joystick_listing = {}
            for item in self.profile_devices:
                self.joystick_listing.update({
                    item[:-48] : item
                })
            for joystick_device, joystick_file in self.joystick_listing.items():
                
                if os.path.isdir(os.path.join(self.fq_path, joystick_file)):
                        print("Skipping as Folder")
                else:
                    try:
                        self.file = Path(os.path.join(self.fq_path, joystick_file)).read_text(encoding="utf-8")
                        self.file = self.file.replace('local diff = ', '') ## CLEAN UP
                        self.file = self.file.replace('return diff', '') ## CLEAN UP
                    except FileNotFoundError:
                        raise FileExistsError("DCS: File {} no longer found - It has been moved/deleted from directory".format(joystick_file))
                    else:
                        data = self.parseFile()
                        writeVal = False
                        buttonArray = {}
                        if 'keyDiffs' in data.keys():
                            for value in data['keyDiffs'].values():
                                for item, attribute in value.items():
                                    if item=='name':
                                        name = attribute
                                    if item=='added':
                                        button = self.convert_button_format(attribute[1]['key'])
                                        writeVal = True
                                if writeVal:
                                    buttonArray.update({
                                        button : name
                                    })
                                    writeVal = False
                            self.update_joystick_dictionary(joystick_device,profile, False, buttonArray)
        return self.joystick_dictionary

    def parseFile(self):
        # pylint: disable=unused-variable
        tokens = ('LCURLY', 'RCURLY', 'STRING', 'NUMBER', 'LBRACE', 'RBRACE', 'COMMA', 'EQUALS', 'TRUE', 'FALSE', 'DOUBLE_VAL')

        t_LCURLY = r"\{"
        t_RCURLY = r"\}"
        t_LBRACE = r"\["
        t_RBRACE = r"\]"
        t_COMMA = r"\,"
        t_EQUALS = r"\="

        def t_DOUBLE_VAL(t):
            r"(\+|\-)?[0-9]+\.[0-9]+"
            t.value = float(t.value)
            return t

        def t_NUMBER(t):
            r"[0-9]+"
            t.value = int(t.value)
            return t

        def t_STRING(t):
            r"\"[\w|\/|\(|\)|\-|\:|\+|\,|\&|\.|\'|\s]+\""
            t.value = t.value[1:-1]
            return t

        def t_TRUE(t):
            r'(true)'
            t.value = True
            return t

        def t_FALSE(t):
            r'(false)'
            t.value = False
            return t

        t_ignore = " \t\n"

        def t_error(t):
            print("Illegal character '%s'" % t.value[0])
            t.lexer.skip(1)

        # Parsing rules

        def p_dict(t):
            """dict : LCURLY dvalues RCURLY"""
            t[0] = t[2]

        def p_dvalues(t):
            """dvalues : dvalue
                    | dvalue COMMA
                    | dvalue COMMA dvalues"""
            t[0] = t[1]
            if len(t) == 4:
                t[0].update(t[3])
                
        def p_key_expression(t):
            """key : LBRACE NUMBER RBRACE
                | LBRACE STRING RBRACE"""
            t[0] = t[2]

        def p_value_expression(t):
            """ dvalue : key EQUALS STRING
            | key EQUALS boolean
            | key EQUALS DOUBLE_VAL
            | key EQUALS NUMBER
            | key EQUALS dict """
            t[0] = {t[1]: t[3]}

        def p_boolean(p):
            ''' boolean : TRUE
                        | FALSE
            '''
            p[0] = p[1]

        def p_error(t):
            print("Syntax error at '%s'" % t.value)

        # Build the lexer
        ## TODO: Consider env vars to run optimize=1 in deployed version
        lexer = lex.lex(
            debug=False,
            optimize=1,
            lextab='dcs_world_lex',
            reflags=re.UNICODE | re.VERBOSE
            )

        # Build the parser
        parser = yacc.yacc(
            debug=False,
            optimize=1,
            tabmodule='dcs_world_parse'
            )

        # Parse the data
        try:
            data = parser.parse(self.file)
        except Exception as error:
            print(error)
        return data