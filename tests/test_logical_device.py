import pytest
from joystick_diagrams.classes.input import Input, Command, Modifier, LogicalDevice


def test_create_modifier_single():
    m = Modifier("ABC", "DEF")

    assert m.modifiers == "ABC"
    assert m.command == "DEF"


def test_create_modifier_multiple():
    m = Modifier(("ABC", "123"), "DEF")

    assert m.modifiers[0] == "ABC"
    assert m.modifiers[1] == "123"
    assert m.command == "DEF"


def test_create_input():
    pass


def test_add_input_to_logical_device():
    pass


def test_add_modifier_to_input():
    pass


def test_adding_existing_input():
    pass
