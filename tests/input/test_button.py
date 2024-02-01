import pytest

from joystick_diagrams.input.button import Button


def test_button_valid():
    id = 1
    button = Button(id)

    assert button.id == id


def test_hat_string_id():
    id = "1"

    with pytest.raises(ValueError):
        Button(id)


def test_hat_identifier_format():
    button = Button(1)

    assert button.identifier == "BUTTON_1"
