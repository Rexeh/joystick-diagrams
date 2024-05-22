import pytest

from joystick_diagrams.input.types.axis import Axis, AxisDirection, AxisSlider

# AXIS TESTS


def test_axis_valid():
    axis = Axis(AxisDirection.X)
    assert axis.id.name == "X"


def test_axis_invalid_key():
    with pytest.raises(KeyError):
        Axis(AxisDirection["x"])


def test_axis_invalid_type():
    with pytest.raises(ValueError):
        Axis("X")


def test_axis_identifier():
    axis = Axis(AxisDirection.X)

    assert axis.identifier == "AXIS_X"


# AXIS SLIDER


def test_axis_slider_valid():
    axis = AxisSlider(1)
    assert axis.id == 1


def test_axis__slider_str():
    with pytest.raises(ValueError):
        AxisSlider("1")


def test_axis_slider_identifier():
    axis = AxisSlider(1)

    assert axis.identifier == "AXIS_SLIDER_1"
