"""Tests for OutputPluginInterface ready-state logic and ExportResult construction."""

from pathlib import Path

import pytest
from pydantic import Field

from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
from joystick_diagrams.plugins.output_plugin_interface import (
    ExportResult,
    OutputPluginInterface,
)
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings

GUID = "666ec0a0-556b-11ee-8002-444553540000"


# ── Concrete test plugins ──


class NoSettingsPlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(name="NoSettings", version="1.0.0", icon_path="img/x.ico")

    def process_export(self, results):
        return True


class RequiredPathSettings(PluginSettings):
    input_path: Path | None = Field(
        default=None,
        title="Input Path",
        json_schema_extra={"is_folder": True},
    )


class RequiredPathPlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(name="ReqPath", version="1.0.0", icon_path="img/x.ico")
    plugin_settings_model = RequiredPathSettings

    def process_export(self, results):
        return True


class OptionalPathSettings(PluginSettings):
    optional_path: Path | None = Field(
        default=None,
        title="Optional",
        json_schema_extra={"is_folder": True, "required": False},
    )


class OptionalPathPlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(name="OptPath", version="1.0.0", icon_path="img/x.ico")
    plugin_settings_model = OptionalPathSettings

    def process_export(self, results):
        return True


class MixedSettings(PluginSettings):
    required_path: Path | None = Field(
        default=None,
        title="Required",
        json_schema_extra={"is_folder": True},
    )
    optional_path: Path | None = Field(
        default=None,
        title="Optional",
        json_schema_extra={"is_folder": True, "required": False},
    )
    some_bool: bool = Field(default=True, title="Toggle")


class MixedPlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(name="Mixed", version="1.0.0", icon_path="img/x.ico")
    plugin_settings_model = MixedSettings

    def process_export(self, results):
        return True


# ── Ready state tests ──


def test_ready_no_settings():
    """Plugin with no settings model is always ready."""
    plugin = NoSettingsPlugin()
    assert plugin.ready is True


def test_ready_required_path_not_set():
    """Plugin with a required path field is not ready when path is None."""
    plugin = RequiredPathPlugin()
    assert plugin.ready is False


def test_ready_required_path_set():
    """Plugin with a required path field is ready once the path is set."""
    plugin = RequiredPathPlugin()
    plugin.update_setting("input_path", Path("/some/path"))
    assert plugin.ready is True


def test_ready_optional_path_not_set():
    """Plugin with only optional path fields is always ready."""
    plugin = OptionalPathPlugin()
    assert plugin.ready is True


def test_ready_mixed_fields_required_unset():
    """Mixed settings: not ready when required path is None, even if optional is set."""
    plugin = MixedPlugin()
    plugin.update_setting("optional_path", Path("/opt"))
    assert plugin.ready is False


def test_ready_mixed_fields_required_set():
    """Mixed settings: ready once required path is set, regardless of optional or bool."""
    plugin = MixedPlugin()
    plugin.update_setting("required_path", Path("/req"))
    assert plugin.ready is True


# ── Metadata tests ──


def test_plugin_meta_name():
    plugin = NoSettingsPlugin()
    assert plugin.name == "NoSettings"
    assert plugin.version == "1.0.0"


def test_missing_plugin_meta_raises():
    with pytest.raises(TypeError, match="must define"):

        class BadPlugin(OutputPluginInterface):
            def process_export(self, results):
                return True

        BadPlugin()


# ── ExportResult construction ──


def test_export_result_fields():
    device = Device_(GUID, "Test Device")
    device.create_input(Button(1), "Fire")

    result = ExportResult(
        profile_name="A-10C II",
        device_name="Test Device",
        device_guid=GUID,
        source_plugin="DCS World",
        template_name="warthog.svg",
        export_format="PNG",
        file_path=Path("test.png"),
        export_directory=Path("/export"),
        device=device,
    )

    assert result.profile_name == "A-10C II"
    assert result.device_guid == GUID
    assert result.source_plugin == "DCS World"
    assert result.export_format == "PNG"
    assert result.device.name == "Test Device"
    # Verify device bindings are accessible
    combined = result.device.get_combined_inputs()
    assert "BUTTON_1" in combined
    assert combined["BUTTON_1"].command == "Fire"


def test_export_result_is_frozen():
    device = Device_(GUID, "Test Device")
    result = ExportResult(
        profile_name="test",
        device_name="dev",
        device_guid=GUID,
        source_plugin="DCS World",
        template_name=None,
        export_format="SVG",
        file_path=Path("test.svg"),
        export_directory=Path("."),
        device=device,
    )
    with pytest.raises(AttributeError):
        result.profile_name = "changed"
