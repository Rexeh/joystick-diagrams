import pytest
from joystick_diagrams.input.input import Input_


@pytest.fixture()
def get_input():
    def _get_input(id: str, operation: str):
        return Input_(id, operation)

    return _get_input


def test_new_input(get_input):
    input_id = "BUTTON_1"
    operation = "Press"
    obj = get_input("BUTTON_1", "Press")

    assert obj.identifier == input_id.lower()
    assert obj.command == operation


def test_new_modifier(get_input):
    input_id = "BUTTON_1"
    operation = "Press"
    obj = get_input("BUTTON_1", "Press")

    assert len(obj.modifiers) == 0

    obj.add_modifier({"ctrl"}, "Modifier Press")

    assert len(obj.modifiers) > 0


def test_existing_modifier(get_input):
    input_id = "BUTTON_1"
    operation = "Press"
    obj = get_input("BUTTON_1", "Press")

    assert len(obj.modifiers) == 0

    obj.add_modifier({"ctrl"}, "Modifier Press")

    assert len(obj.modifiers) == 1
    assert obj.modifiers[0].modifiers == {"ctrl"}
    assert obj.modifiers[0].command == "Modifier Press"

    obj.add_modifier({"ctrl"}, "Modifier Altered")

    assert len(obj.modifiers) == 1
    assert obj.modifiers[0].command == "Modifier Altered"
