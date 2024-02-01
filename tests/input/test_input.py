import pytest

from joystick_diagrams.input.axis import Axis, AxisDirection, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat, HatDirection
from joystick_diagrams.input.input import Input_


def test_new_button_input_valid():
    new_input = Input_(Button(1), "created")
    assert new_input.command == "created"
    assert isinstance(new_input.input_control, Button)


def test_new_button_input_valid_type():
    with pytest.raises(ValueError):
        Input_("1", "created")


def test_new_hat_input_valid():
    new_input = Input_(Hat(1, HatDirection.D), "created")
    assert new_input.command == "created"
    assert isinstance(new_input.input_control, Hat)


def test_new_axis_input_valid():
    new_input = Input_(Axis(AxisDirection.X), "created")
    assert new_input.command == "created"
    assert isinstance(new_input.input_control, Axis)


def test_new_axis_slider_input_valid():
    new_input = Input_(AxisSlider(1), "created")
    assert new_input.command == "created"
    assert isinstance(new_input.input_control, AxisSlider)


def test_new_modifier_existing_input():
    new_input = Input_(Button(1), "created")
    assert len(new_input.modifiers) == 0
    new_input.add_modifier({"ctrl"}, "modifier")
    assert len(new_input.modifiers) == 1


def test_existing_modifier():
    new_input = Input_(Button(1), "created")
    new_input.add_modifier({"ctrl"}, "modifier")

    assert new_input.modifiers[0].modifiers == {"ctrl"}
    assert new_input.modifiers[0].command == "modifier"

    new_input.add_modifier({"ctrl"}, "changed")
    assert new_input.modifiers[0].command == "changed"
    assert new_input.modifiers[0].modifiers == {"ctrl"}
    assert len(new_input.modifiers) == 1


def test_input_repr():
    new_input = Input_(Button(1), "created")
    new_input.add_modifier({"ctrl"}, "mod")
    assert new_input.__repr__() == "Button(id=1) - created - [Modifier(modifiers={'ctrl'}, command='mod')]"


def test_input_str():
    new_input = Input_(Button(1), "created")
    new_input.add_modifier({"ctrl"}, "mod")
    assert new_input.__str__() == "created - ['mod - ctrl']"


def test_input_identifier():
    """Covered primarily by individual control type tests"""
    new_input = Input_(Button(1), "created")
    assert new_input.identifier == "BUTTON_1"
