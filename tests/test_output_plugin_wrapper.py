"""Tests for OutputPluginWrapper run gating and error handling."""

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import Field

from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
from joystick_diagrams.output_plugin_wrapper import OutputPluginWrapper
from joystick_diagrams.plugins.output_plugin_interface import (
    ExportResult,
    OutputPluginInterface,
)
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings

GUID = "666ec0a0-556b-11ee-8002-444553540000"


class SimplePlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(name="Simple", version="1.0.0", icon_path="img/x.ico")

    def __init__(self):
        super().__init__()
        self.received_results = None

    def process_export(self, results):
        self.received_results = results
        return True


class FailingPlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(name="Failing", version="1.0.0", icon_path="img/x.ico")

    def process_export(self, results):
        raise RuntimeError("something broke")


class RequiredPathSettings(PluginSettings):
    path: Path | None = Field(
        default=None,
        title="Path",
        json_schema_extra={"is_folder": True},
    )


class NotReadyPlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(name="NotReady", version="1.0.0", icon_path="img/x.ico")
    plugin_settings_model = RequiredPathSettings

    def process_export(self, results):
        return True


@pytest.fixture
def sample_results():
    device = Device_(GUID, "Test Device")
    device.create_input(Button(1), "Fire")
    return [
        ExportResult(
            profile_name="A-10C",
            device_name="Test Device",
            device_guid=GUID,
            source_plugin="DCS World",
            template_name=None,
            export_format="PNG",
            file_path=Path("test.png"),
            export_directory=Path("."),
            device=device,
        )
    ]


@pytest.fixture
def wrapper():
    """Create wrapper with DB calls mocked."""
    with patch("joystick_diagrams.output_plugin_wrapper.db_plugin_data"):
        return OutputPluginWrapper(SimplePlugin())


@pytest.fixture
def failing_wrapper():
    with patch("joystick_diagrams.output_plugin_wrapper.db_plugin_data"):
        return OutputPluginWrapper(FailingPlugin())


@pytest.fixture
def not_ready_wrapper():
    with patch("joystick_diagrams.output_plugin_wrapper.db_plugin_data"):
        return OutputPluginWrapper(NotReadyPlugin())


def test_run_disabled_skips_plugin(wrapper, sample_results):
    """Disabled wrapper should skip execution and return True."""
    wrapper._enabled = False
    result = wrapper.run(sample_results)
    assert result is True
    assert wrapper.plugin.received_results is None


def test_run_enabled_calls_process_export(wrapper, sample_results):
    """Enabled and ready wrapper should call process_export with results."""
    wrapper._enabled = True
    result = wrapper.run(sample_results)
    assert result is True
    assert wrapper.plugin.received_results == sample_results


def test_run_not_ready_skips_plugin(not_ready_wrapper, sample_results):
    """Wrapper with unmet required paths should skip execution."""
    not_ready_wrapper._enabled = True
    result = not_ready_wrapper.run(sample_results)
    assert result is True


def test_run_catches_exception(failing_wrapper, sample_results):
    """Wrapper should catch exceptions from process_export and return False."""
    failing_wrapper._enabled = True
    result = failing_wrapper.run(sample_results)
    assert result is False
    assert "something broke" in failing_wrapper._error


def test_wrapper_properties(wrapper):
    assert wrapper.name == "Simple"
    assert wrapper.version == "1.0.0"
    assert wrapper.has_settings() is False


def test_enabled_toggle_persists(wrapper):
    """Toggling enabled state should call store_plugin_configuration."""
    with patch.object(wrapper, "store_plugin_configuration") as mock_store:
        wrapper.enabled = True
        assert wrapper.enabled is True
        mock_store.assert_called_once()
