from xml.dom import minidom
import functions.helper as helper
import os
import ply.lex as lex
import ply.yacc as yacc
import json
import pprint
from pathlib import Path

dirSift = '_easy'
inherit = 'Default'
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
    r"\"[\w|\/|\(|\)|\-|\:|\+|\s]+\""
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

# JOY_BTNX = BUTTON
# JOY_Z/Y/X = AXIS

# ["added"] = {
# 				[1] = {
# 					["filter"] = {
# 						["curvature"] = {
# 							[1] = 0,
# 						},
# 						["deadzone"] = 0,
# 						["invert"] = true,
# 						["saturationX"] = 1,
# 						["saturationY"] = 1,
# 						["slider"] = false,
# 					},
# 					["key"] = "JOY_RX",

class DCS_World:

    BaseDirectory = './tests/data/DCS_World/input'
    JoystickListing = {}
    SeekDirectories = 'joystick'

    ## Get Input Directory
    DCS_Profiles = os.listdir(BaseDirectory)
    ## Remove _EASY directories
    Filtered_Profiles = list(filter(lambda x: False if dirSift in x else True, DCS_Profiles))

    print(Filtered_Profiles)

    CurrentProfileDirectory = os.path.join(BaseDirectory, Filtered_Profiles[7],SeekDirectories)

    # Try get Joystick Directory
    try:
        Profile_Devices = os.listdir(os.path.join(BaseDirectory, Filtered_Profiles[7],SeekDirectories))
    except:
        print("Error Profile does not have joystick directory")

    ## IF PRFILE DEVICE IS A DIRECTORY
        # HANDLE ERROR
        
    ## ASSUMING DIR FOUND - Process the Device Names
    print("Number of devices for Profile: {}".format(len(Profile_Devices)))
    for profile in Profile_Devices:
        JoystickListing.update({
            profile[:-48] : profile
        })
    
    ## For Each Device, Go Parse the Stuff
    print(JoystickListing)

    for joystick_name, joystick_file in JoystickListing.items():
        print(joystick_name)
        print(joystick_file)
        try:
            file = Path(os.path.join(CurrentProfileDirectory, joystick_file)).read_text()
        except Exception as error:
            print("File not found: {}".format(error))

        #Fix this later hack to get parser working
        file = file.replace('local diff = ', '')
        file = file.replace('return diff', '')
 
        print("Input File: {}".format(file))

        tokens = ('LCURLY', 'RCURLY', 'STRING', 'NUMBER', 'LBRACE', 'RBRACE', 'COMMA', 'EQUALS', 'TRUE', 'FALSE', 'DOUBLE_VAL')

        # Build the lexer
        lexer = lex.lex()

        # Build the parser
        parser = yacc.yacc()

        # Parse the data
        data = parser.parse(file)

        print(data)

        # pp.pprint(data['keyDiffs'])

        # for i in data['keyDiffs'].values():
        # 	print (i['name'])
        # 	if 'added' in i:
        # 		print (i['added'][1]['key'])

