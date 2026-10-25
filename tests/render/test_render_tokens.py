import re

import pytest

from joystick_diagrams.render.slots import SlotRole
from joystick_diagrams.render.tokens import BLANK_RE, FILL_RE, classify, find_tokens
from joystick_diagrams.template import Template
from tests.render.render_fixtures import CORPUS

LEGACY = [
    Template.BUTTON_KEY,
    Template.AXIS_KEY,
    Template.HAT_KEY,
    *Template.MODIFIER_KEYS,
]


@pytest.mark.parametrize(
    ("token", "role", "input_key", "index"),
    [
        ("BUTTON_1", SlotRole.ACTION, "button_1", None),
        ("button_12", SlotRole.ACTION, "button_12", None),
        ("AXIS_X", SlotRole.ACTION, "axis_x", None),
        ("Axis_RX", SlotRole.ACTION, "axis_rx", None),
        ("AXIS_SLIDER_1", SlotRole.ACTION, "axis_slider_1", None),
        ("AXIS_SLIDER_10", SlotRole.ACTION, "axis_slider_10", None),
        ("POV_1_U", SlotRole.ACTION, "pov_1_u", None),
        ("POV_2_DL", SlotRole.ACTION, "pov_2_dl", None),
        ("BUTTON_1_MODIFIERS", SlotRole.MODIFIERS, "button_1", None),
        ("BUTTON_1_MODIFIER_2", SlotRole.MODIFIER, "button_1", 2),
        ("AXIS_X_Modifier_1_Key", SlotRole.MODIFIER_KEY, "axis_x", 1),
        ("POV_1_UR_MODIFIER_3_ACTION", SlotRole.MODIFIER_ACTION, "pov_1_ur", 3),
        ("TEMPLATE_NAME", SlotRole.TITLE, None, None),
        ("current_date", SlotRole.DATE, None, None),
        # legacy-only shapes: blanked, never filled
        ("POV_1_LL", SlotRole.UNKNOWN, None, None),
        ("BUTTON_1_MODIFIER_1_STYLE", SlotRole.UNKNOWN, "button_1", None),
        ("BUTTON_1_MODIFIER_1_COMMAND", SlotRole.UNKNOWN, "button_1", None),
        ("AXIS_X1", SlotRole.UNKNOWN, None, None),
    ],
)
def test_classify(token, role, input_key, index):
    info = classify(token)
    assert info.role is role
    assert info.input_key == input_key
    assert info.modifier_index == index
    assert info.token == token.lower()


def test_blank_matches_every_fill_token():
    for token in ["BUTTON_1", "AXIS_SLIDER_10", "POV_1_UR", "BUTTON_1_MODIFIER_1_KEY"]:
        assert FILL_RE.fullmatch(token)
        assert BLANK_RE.fullmatch(token)


def test_blank_is_case_insensitive_and_word_bounded():
    assert find_tokens("x Button_1 y") == ["button_1"]
    assert find_tokens("XBUTTON_1") == []
    assert find_tokens("BUTTON_1x") == []
    assert find_tokens("BUTTON_1_MODIFIER_1_KEY") == ["button_1_modifier_1_key"]
    assert find_tokens("AXIS_X_MODIFIERS") == ["axis_x_modifiers"]
    assert find_tokens("BUTTON_62<br>BUTTON_35") == ["button_62", "button_35"]


@pytest.mark.parametrize(
    "text",
    [
        "POV_1_LL",
        "AXIS_X1",
        "AXIS_SLIDER_",
        "BUTTON_1_MODIFIER_1_STYLE",
        "FOO_BAR_MODIFIER_9_WHATEVER",
        "POV_1_UUDD",
    ],
)
def test_blank_is_superset_of_legacy_on_edge_tokens(text):
    legacy_hits = {m for pat in LEGACY for m in pat.findall(text)}
    assert legacy_hits, "sanity: legacy blanks this"
    assert BLANK_RE.sub("", text) == ""


@pytest.mark.parametrize("path", CORPUS, ids=lambda p: p.name)
def test_blank_is_superset_of_legacy_over_corpus(path):
    text = path.read_text(encoding="utf-8")
    legacy_hits: set[str] = set()
    for pattern in LEGACY:
        legacy_hits.update(pattern.findall(text))
    unmatched = {hit for hit in legacy_hits if not BLANK_RE.fullmatch(hit)}
    assert not unmatched


def test_single_pass_alternation_prefers_longest_modifier_form():
    # the legacy generic forms must not swallow part of a stricter token
    matches = [
        m.group(0) for m in BLANK_RE.finditer("BUTTON_1_MODIFIER_1_KEY BUTTON_1")
    ]
    assert matches == ["BUTTON_1_MODIFIER_1_KEY", "BUTTON_1"]
    assert re.fullmatch(BLANK_RE, "AXIS_SLIDER_1_MODIFIER_2")
