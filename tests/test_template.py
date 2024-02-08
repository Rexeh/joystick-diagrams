from pathlib import Path

import pytest

from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.template import Template


@pytest.fixture
def get_template_path_valid():
    return Path("tests/data/template_test.svg")


def test_template_set_success(get_template_path_valid):
    setup_template = Template(get_template_path_valid)
    assert isinstance(setup_template, Template)


def test_template_set_failure():
    with pytest.raises(JoystickDiagramsError):
        Template("")


def test_template_hat_property(get_template_path_valid):
    expected_hats = {
        "pov_1_r",
        "pov_2_d",
        "pov_1_l",
        "pov_1_dl",
        "pov_1_ur",
        "pov_2_l",
        "pov_1_dr",
        "pov_2_r",
        "pov_1_ul",
        "pov_1_d",
        "pov_1_u",
        "pov_2_u",
    }
    setup_template = Template(get_template_path_valid)

    assert setup_template.hat_count == 12
    assert setup_template.hats == expected_hats


def test_template_axis_property(get_template_path_valid):
    expected_axis = {"axis_x", "axis_y", "axis_rx", "axis_slider_1", "axis_z"}
    setup_template = Template(get_template_path_valid)

    assert setup_template.axis_count == 5
    assert setup_template.axis == expected_axis


def test_template_button_property(get_template_path_valid):
    expected_buttons = {"button_1", "button_2", "button_10"}
    setup_template = Template(get_template_path_valid)

    assert setup_template.button_count == 3
    assert setup_template.buttons == expected_buttons


def test_template_modifiers_property(get_template_path_valid):
    expected_modifiers = {"button_1_mod_1", "button_1_mod_2", "button_2_mod_1"}
    setup_template = Template(get_template_path_valid)

    assert setup_template.modifier_count == 3
    assert setup_template.modifiers == expected_modifiers


def test_template_template_name_exists(get_template_path_valid):
    setup_template = Template(get_template_path_valid)
    assert setup_template.template_name is True


def test_template_template_name_missing(get_template_path_valid):
    setup_template = Template(get_template_path_valid)
    import re

    setup_template.raw_data = re.sub(
        Template.TEMPLATE_NAMING_KEY,
        "",
        setup_template.raw_data,
        flags=re.IGNORECASE,
    )
    assert setup_template.template_name is False


def test_template_current_date_exists(get_template_path_valid):
    setup_template = Template(get_template_path_valid)
    assert setup_template.date is True


def test_template_template_date_missing(get_template_path_valid):
    setup_template = Template(get_template_path_valid)
    import re

    setup_template.raw_data = re.sub(
        Template.TEMPLATE_DATE_KEY,
        "",
        setup_template.raw_data,
        flags=re.IGNORECASE,
    )
    assert setup_template.date is False
