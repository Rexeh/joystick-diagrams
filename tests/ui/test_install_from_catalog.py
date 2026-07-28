"""Tests for the catalog-driven install flow.

Covers the behaviour the store and the first-run picker share: a plugin the user
deliberately chose must come back enabled, and a plugin that cannot be located after
the manager reload must not turn a successful install into a crash.
"""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.plugins import plugin_catalog as pc  # noqa: E402
from joystick_diagrams.ui import plugin_install_flow as flow  # noqa: E402


def _entry(plugin_type="parser"):
    return pc.CatalogEntry(
        id=str(uuid4()),
        name="DCS World",
        type=plugin_type,
        version="1.0.0",
        download_url="https://example.com/p.zip",
        sha256="0" * 64,
    )


def _app_state():
    state = MagicMock()
    state.plugin_manager.plugin_wrappers = []
    state.output_plugin_manager.plugin_wrappers = []
    return state


@pytest.mark.uitest
def test_enables_the_newly_installed_plugin(qapp, tmp_path):
    installed = tmp_path / "dcs_world"
    installed.mkdir()
    wrapper = SimpleNamespace(name="DCS World", enabled=False)
    state = _app_state()
    state.plugin_manager.plugin_wrappers = [wrapper]

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "DCS World"),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True) as mock_record,
        patch.object(flow, "reload_plugin_manager", autospec=True) as mock_reload,
    ):
        result = flow.install_from_catalog(_entry(), state, None)

    assert result == "DCS World"
    assert wrapper.enabled is True
    mock_record.assert_called_once_with("DCS World", "parser", installed)
    mock_reload.assert_called_once_with(state, "parser")


@pytest.mark.uitest
def test_output_plugin_is_enabled_on_the_output_manager(qapp, tmp_path):
    installed = tmp_path / "exporter"
    installed.mkdir()
    wrapper = SimpleNamespace(name="DCS World", enabled=False)
    state = _app_state()
    state.output_plugin_manager.plugin_wrappers = [wrapper]

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "DCS World"),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True),
        patch.object(flow, "reload_plugin_manager", autospec=True),
    ):
        flow.install_from_catalog(_entry("output"), state, None)

    assert wrapper.enabled is True


@pytest.mark.uitest
def test_install_still_succeeds_when_the_new_wrapper_cannot_be_found(qapp, tmp_path):
    installed = tmp_path / "dcs_world"
    installed.mkdir()
    state = _app_state()

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "DCS World"),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True),
        patch.object(flow, "reload_plugin_manager", autospec=True),
    ):
        result = flow.install_from_catalog(_entry(), state, None)

    assert result == "DCS World"
