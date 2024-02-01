import pytest

from joystick_diagrams.input.modifier import Modifier


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
