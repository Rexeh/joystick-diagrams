"""Tests for the shared local-source install flow."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.ui import plugin_install_flow as flow  # noqa: E402


class _FakeManager:
    plugin_wrappers: list = []

    def is_user_plugin(self, name):
        return True


def _app_state():
    state = MagicMock()
    state.plugin_manager = _FakeManager()
    return state


@pytest.mark.uitest
def test_returns_plugin_name_on_success(qapp, tmp_path):
    installed = tmp_path / "my_plugin"
    installed.mkdir()

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "My Plugin"),
        ),
        patch.object(flow, "run_security_check", return_value=True),
        patch.object(flow, "record_trust"),
        patch.object(flow, "reload_plugin_manager"),
    ):
        result = flow.install_from_local_source(Path("plugin.zip"), _app_state(), None)

    assert result == "My Plugin"


@pytest.mark.uitest
def test_returns_none_and_removes_plugin_when_trust_declined(qapp, tmp_path):
    installed = tmp_path / "my_plugin"
    installed.mkdir()

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "My Plugin"),
        ),
        patch.object(flow, "run_security_check", return_value=False),
        patch.object(flow, "reload_plugin_manager"),
    ):
        result = flow.install_from_local_source(Path("plugin.zip"), _app_state(), None)

    assert result is None
    assert not installed.exists()


@pytest.mark.uitest
def test_returns_none_when_installer_raises(qapp):
    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            side_effect=OSError("bad zip"),
        ),
        patch("PySide6.QtWidgets.QMessageBox.warning"),
    ):
        result = flow.install_from_local_source(Path("plugin.zip"), _app_state(), None)

    assert result is None
