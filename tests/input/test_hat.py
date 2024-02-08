#
import pytest

from joystick_diagrams.input.hat import Hat, HatDirection


def test_hat_valid():
    hat_id = 1
    direction = HatDirection.U

    hat = Hat(hat_id, direction)

    assert hat.id == hat_id
    assert hat.direction == direction


def test_hat_string_id():
    hat_id = "1"
    direction = HatDirection.U

    with pytest.raises(ValueError):
        Hat(hat_id, direction)


def test_hat_invalid_hat_direction_string():
    hat_id = 1
    direction = "U"

    with pytest.raises(ValueError):
        Hat(hat_id, direction)


def test_hat_invalid_hat_direction_key():
    with pytest.raises(KeyError):
        Hat(1, HatDirection["O"])


def test_hat_identifier_format():
    hat_id = 1
    direction = HatDirection.U

    hat = Hat(hat_id, direction)

    assert hat.identifier == "POV_1_U"
