# lextab.py. This file automatically created by PLY (version 3.11). Don't edit!
_tabversion = "3.10"
_lextokens = set(
    (
        "COMMA",
        "DOUBLE_VAL",
        "EQUALS",
        "FALSE",
        "LBRACE",
        "LCURLY",
        "NUMBER",
        "RBRACE",
        "RCURLY",
        "STRING",
        "TRUE",
    )
)
_lexreflags = 96
_lexliterals = ""
_lexstateinfo = {"INITIAL": "inclusive"}
_lexstatere = {
    "INITIAL": [
        (
            '(?P<t_DOUBLE_VAL>(\\+|\\-)?[0-9]+\\.[0-9]+)|(?P<t_NUMBER>[0-9]+)|(?P<t_STRING>\\"([^\\"\\\\]|\\\\.)*\\" )|(?P<t_TRUE>(true))|(?P<t_FALSE>(false))|(?P<t_LCURLY>\\{)|(?P<t_RCURLY>\\})|(?P<t_LBRACE>\\[)|(?P<t_RBRACE>\\])|(?P<t_COMMA>\\,)|(?P<t_EQUALS>\\=)',
            [
                None,
                ("t_DOUBLE_VAL", "DOUBLE_VAL"),
                None,
                ("t_NUMBER", "NUMBER"),
                ("t_STRING", "STRING"),
                None,
                ("t_TRUE", "TRUE"),
                None,
                ("t_FALSE", "FALSE"),
                None,
                (None, "LCURLY"),
                (None, "RCURLY"),
                (None, "LBRACE"),
                (None, "RBRACE"),
                (None, "COMMA"),
                (None, "EQUALS"),
            ],
        )
    ]
}
_lexstateignore = {"INITIAL": " \t\n"}
_lexstateerrorf = {"INITIAL": "t_error"}
_lexstateeoff = {}
