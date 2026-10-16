from types import SimpleNamespace
from unittest.mock import patch

from joystick_diagrams.ui.device_setup import DeviceSetup


def test_child_profile_name_is_visible_in_primary_column(qtbot):
    fake_state = SimpleNamespace(
        device_service=SimpleNamespace(resolve_name=lambda _guid, name: name)
    )
    profile = SimpleNamespace(
        profile_name="Default",
        profile_origin=SimpleNamespace(icon=""),
    )
    export_device = SimpleNamespace(
        device_id="x52-guid",
        device_name="Saitek X52 Pro 2024 Planes",
        profile_wrapper=profile,
        has_template=True,
        errors=[],
    )

    with (
        patch("joystick_diagrams.ui.device_setup.AppState", return_value=fake_state),
        patch("joystick_diagrams.ui.device_setup.get_export_devices", return_value=[]),
        patch(
            "joystick_diagrams.ui.device_setup.get_device_template_path",
            return_value="x52.svg",
        ),
    ):
        widget = DeviceSetup()
        qtbot.addWidget(widget)
        widget.add_devices_to_widget([export_device])

    root = widget.treeWidget.topLevelItem(0)
    child = root.child(0)

    assert child.text(0) == "Default"
    assert child.text(1) == ""
