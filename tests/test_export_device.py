import os

import pytest

from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.input.axis import Axis, AxisDirection
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.hat import Hat, HatDirection
from joystick_diagrams.template import Template

DATA_DIR = "tests/data/"
TEST_FILE = "template_test.svg"


@pytest.fixture()
def device():
    dev = Device_("12345678-1234-5678-1234-567812345678", "Test Device")
    dev.create_input(Button(90), "Button One Action")
    dev.create_input(Button(2), "Button Two Action")
    dev.create_input(Axis(AxisDirection.X), "AXIS X Action")
    dev.create_input(Axis(AxisDirection.Y), "AXIS Y Action")
    dev.create_input(Axis(AxisDirection.RZ), "AXIS Y Action")
    dev.create_input(Hat(1, HatDirection.D), "Hat Down Action")
    dev.create_input(Hat(3, HatDirection.U), "Hat Up Action")
    dev.add_modifier_to_input(Button(1), {"ctrl"}, "Modifier Action")
    return dev


@pytest.fixture()
def profile_wrapper():
    # Not required for Export Device tests
    return None


@pytest.fixture()
def no_template():
    return None


@pytest.fixture()
def template() -> Template:
    return Template(os.path.join(DATA_DIR, TEST_FILE))


@pytest.fixture()
def export_device(device, profile_wrapper, no_template) -> ExportDevice:
    return ExportDevice(device, no_template, profile_wrapper)


def test_export_device_creation(export_device):
    ed = export_device
    assert isinstance(ed, ExportDevice)


def test_device_id_property(export_device):
    assert export_device.device_id == "12345678-1234-5678-1234-567812345678"


def test_device_name_property(export_device):
    assert export_device.device_name == "Test Device"


def test_template_check(export_device):
    assert export_device.has_template is False


def test_get_template_when_none(export_device):
    assert export_device.template is None


def test_template_set(export_device, template):
    export_device.template = template

    assert export_device.template == template
    assert export_device.errors is not None


def test_template_compatibility(export_device, template):
    export_device.template = template

    check = export_device.check_compatibility()

    assert "pov_3_u" in check
    assert "axis_rz" in check
    assert "button_90" in check


def test_template_file_name(export_device, template):
    export_device.template = template
    assert export_device.template_file_name == TEST_FILE


def test_template_file_name_no_template(export_device):
    assert export_device.template_file_name is None
