import pytest

from joystick_diagrams.input.button import Button


def test_button_valid():
    button_id = 1
    button = Button(button_id)

    assert button.id == button_id


def test_hat_string_id():
    button_id = "1"

    with pytest.raises(ValueError):
        Button(button_id)


def test_hat_identifier_format():
    button = Button(1)

    assert button.identifier == "BUTTON_1"
