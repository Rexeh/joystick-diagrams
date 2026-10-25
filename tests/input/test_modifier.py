from copy import deepcopy
from dataclasses import replace

import pytest

from joystick_diagrams.input.modifier import (
    Modifier,
    ModifierKind,
    modifier_sort_key,
    normalise_token,
    ordered_keys,
    split_side,
)


def test_modifier_valid():
    mod = Modifier({"ctrl"}, "test")

    assert mod.command == "test"
    assert len(mod.modifiers) == 1


def test_modifier_invalid_set():
    with pytest.raises(ValueError):
        Modifier("ctrl", "test")


def test_modifier_invalid_command_int():
    with pytest.raises(ValueError):
        Modifier({"ctrl"}, 191929)


def test_modifier_invalid_command_set():
    with pytest.raises(ValueError):
        Modifier({"ctrl"}, {"ctrl"})


# ── Kind and source ───────────────────────────────────────────────────


def test_modifier_default_kind_is_key_and_source_none():
    mod = Modifier({"ctrl"}, "test")
    assert mod.kind is ModifierKind.KEY
    assert mod.source is None


def test_modifier_positional_construction_still_works():
    mod = Modifier({"ctrl"}, "test", ModifierKind.QUALIFIER, "profile")
    assert mod.kind is ModifierKind.QUALIFIER
    assert mod.source == "profile"


def test_modifier_kind_accepts_string_value():
    mod = Modifier({"ctrl"}, "test", kind="QUALIFIER")
    assert mod.kind is ModifierKind.QUALIFIER


def test_modifier_invalid_kind_rejected():
    with pytest.raises(ValueError, match="kind"):
        Modifier({"ctrl"}, "test", kind="LABEL")


def test_modifier_invalid_source_rejected():
    with pytest.raises(ValueError, match="source"):
        Modifier({"ctrl"}, "test", source=42)


def test_modifier_equality_and_repr_ignore_kind_and_source():
    """Dedup is set-only: kind/source take no part in eq or repr (plan 2.3)."""
    key = Modifier({"Shift"}, "cmd")
    qualifier = Modifier({"Shift"}, "cmd", kind=ModifierKind.QUALIFIER, source="x")
    assert key == qualifier
    assert repr(qualifier) == "Modifier(modifiers={'Shift'}, command='cmd')"


def test_modifier_replace_and_deepcopy_keep_kind_and_source():
    mod = Modifier({"Long"}, "cmd", kind=ModifierKind.QUALIFIER, source="route")
    copied = replace(mod, command="other")
    assert copied.kind is ModifierKind.QUALIFIER
    assert copied.source == "route"
    assert copied.command == "other"
    cloned = deepcopy(mod)
    assert cloned.kind is ModifierKind.QUALIFIER
    assert cloned.source == "route"
    assert cloned.modifiers is not mod.modifiers


# ── Ordering ──────────────────────────────────────────────────────────


def test_str_single_key_unchanged():
    assert str(Modifier({"ctrl"}, "Fire")) == "Fire - ctrl"


def test_str_uses_built_in_rank_order():
    mod = Modifier({"LShift", "LCtrl"}, "Fire")
    assert str(mod) == "Fire - LCtrl+LShift"
    assert mod.sorted_keys == ("LCtrl", "LShift")


def test_rank_ctrl_alt_shift_win_then_others_alphabetical():
    keys = {"rwin", "BMS DX Shift", "lalt", "JOY_BTN3", "Shift", "control", "Apps"}
    assert ordered_keys(keys) == (
        "control",
        "lalt",
        "Shift",
        "rwin",
        "Apps",
        "BMS DX Shift",
        "JOY_BTN3",
    )


def test_rank_is_stable_for_case_variants():
    assert ordered_keys({"SHIFT", "shift", "Shift"}) == ("SHIFT", "Shift", "shift")
    assert modifier_sort_key("LCtrl")[:2] == (0, "ctrl")
    assert modifier_sort_key("Lever")[:2] == (4, "lever")


def test_split_side_only_strips_known_names():
    assert split_side("LShift") == ("L", "shift")
    assert split_side("Right Ctrl") == ("R", "ctrl")
    assert split_side("l-alt") == ("L", "alt")
    assert split_side("lalt") == ("L", "alt")
    assert split_side("lever") == (None, "lever")
    assert split_side("rudder") == (None, "rudder")
    assert split_side("Shift") == (None, "shift")


def test_normalise_token_collapses_whitespace_and_casefolds():
    assert normalise_token("  BMS   DX  Shift ") == "bms dx shift"
