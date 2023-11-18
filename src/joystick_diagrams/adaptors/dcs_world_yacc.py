# dcs_world_yacc.py
# This file is automatically generated. Do not edit.
# pylint: disable=W,C,R
_tabversion = "3.10"

_lr_method = "LALR"

_lr_signature = "COMMA DOUBLE_VAL EQUALS FALSE LBRACE LCURLY NUMBER RBRACE RCURLY STRING TRUEdict : LCURLY dvalues RCURLYdvalues : dvalue\n            | dvalue COMMA\n            | dvalue COMMA dvalueskey : LBRACE NUMBER RBRACE\n            | LBRACE STRING RBRACEdvalue : key EQUALS STRING\n            | key EQUALS boolean\n            | key EQUALS DOUBLE_VAL\n            | key EQUALS NUMBER\n            | key EQUALS dictboolean : TRUE\n            | FALSE\n            "

_lr_action_items = {
    "LCURLY": (
        [
            0,
            9,
        ],
        [
            2,
            2,
        ],
    ),
    "$end": (
        [
            1,
            7,
        ],
        [
            0,
            -1,
        ],
    ),
    "LBRACE": (
        [
            2,
            8,
        ],
        [
            6,
            6,
        ],
    ),
    "RCURLY": (
        [
            3,
            4,
            7,
            8,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
        ],
        [
            7,
            -2,
            -1,
            -3,
            -4,
            -7,
            -8,
            -9,
            -10,
            -11,
            -12,
            -13,
        ],
    ),
    "COMMA": (
        [
            4,
            7,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
        ],
        [
            8,
            -1,
            -7,
            -8,
            -9,
            -10,
            -11,
            -12,
            -13,
        ],
    ),
    "EQUALS": (
        [
            5,
            20,
            21,
        ],
        [
            9,
            -5,
            -6,
        ],
    ),
    "NUMBER": (
        [
            6,
            9,
        ],
        [
            10,
            16,
        ],
    ),
    "STRING": (
        [
            6,
            9,
        ],
        [
            11,
            13,
        ],
    ),
    "DOUBLE_VAL": (
        [
            9,
        ],
        [
            15,
        ],
    ),
    "TRUE": (
        [
            9,
        ],
        [
            18,
        ],
    ),
    "FALSE": (
        [
            9,
        ],
        [
            19,
        ],
    ),
    "RBRACE": (
        [
            10,
            11,
        ],
        [
            20,
            21,
        ],
    ),
}

_lr_action = {}
for _k, _v in _lr_action_items.items():
    for _x, _y in zip(_v[0], _v[1]):
        if not _x in _lr_action:
            _lr_action[_x] = {}
        _lr_action[_x][_k] = _y
del _lr_action_items

_lr_goto_items = {
    "dict": (
        [
            0,
            9,
        ],
        [
            1,
            17,
        ],
    ),
    "dvalues": (
        [
            2,
            8,
        ],
        [
            3,
            12,
        ],
    ),
    "dvalue": (
        [
            2,
            8,
        ],
        [
            4,
            4,
        ],
    ),
    "key": (
        [
            2,
            8,
        ],
        [
            5,
            5,
        ],
    ),
    "boolean": (
        [
            9,
        ],
        [
            14,
        ],
    ),
}

_lr_goto = {}
for _k, _v in _lr_goto_items.items():
    for _x, _y in zip(_v[0], _v[1]):
        if not _x in _lr_goto:
            _lr_goto[_x] = {}
        _lr_goto[_x][_k] = _y
del _lr_goto_items
_lr_productions = [
    ("S' -> dict", "S'", 1, None, None, None),
    ("dict -> LCURLY dvalues RCURLY", "dict", 3, "p_dict", "dcs_world.py", 228),
    ("dvalues -> dvalue", "dvalues", 1, "p_dvalues", "dcs_world.py", 232),
    ("dvalues -> dvalue COMMA", "dvalues", 2, "p_dvalues", "dcs_world.py", 233),
    ("dvalues -> dvalue COMMA dvalues", "dvalues", 3, "p_dvalues", "dcs_world.py", 234),
    ("key -> LBRACE NUMBER RBRACE", "key", 3, "p_key_expression", "dcs_world.py", 240),
    ("key -> LBRACE STRING RBRACE", "key", 3, "p_key_expression", "dcs_world.py", 241),
    ("dvalue -> key EQUALS STRING", "dvalue", 3, "p_value_expression", "dcs_world.py", 245),
    ("dvalue -> key EQUALS boolean", "dvalue", 3, "p_value_expression", "dcs_world.py", 246),
    ("dvalue -> key EQUALS DOUBLE_VAL", "dvalue", 3, "p_value_expression", "dcs_world.py", 247),
    ("dvalue -> key EQUALS NUMBER", "dvalue", 3, "p_value_expression", "dcs_world.py", 248),
    ("dvalue -> key EQUALS dict", "dvalue", 3, "p_value_expression", "dcs_world.py", 249),
    ("boolean -> TRUE", "boolean", 1, "p_boolean", "dcs_world.py", 253),
    ("boolean -> FALSE", "boolean", 1, "p_boolean", "dcs_world.py", 254),
]
