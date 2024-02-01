#
import pytest

from joystick_diagrams.input.hat import Hat, HatDirection


def test_hat_valid():
    id = 1
    direction = HatDirection.U

    hat = Hat(id, direction)

    assert hat.id == id
    assert hat.direction == direction


def test_hat_string_id():
    id = "1"
    direction = HatDirection.U

    with pytest.raises(ValueError):
        hat = Hat(id, direction)


def test_hat_invalid_hat_direction_string():
    id = 1
    direction = "U"

    with pytest.raises(ValueError):
        hat = Hat(id, direction)


def test_hat_invalid_hat_direction_key():
    with pytest.raises(KeyError):
        hat = Hat(1, HatDirection["O"])


def test_hat_identifier_format():
    id = 1
    direction = HatDirection.U

    hat = Hat(id, direction)

    assert hat.identifier == "POV_1_U"
