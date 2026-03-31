"""Tests for OutputPluginManager discovery and loading."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from joystick_diagrams import exceptions
from joystick_diagrams.plugins import output_plugin_manager
from joystick_diagrams.plugins.output_plugin_manager import (
    _check_folder_validity,
    load_output_plugin,
)


def test_load_output_plugin_invalid_module():
    """Loading a non-existent plugin module raises PluginNotValidError."""
    with pytest.raises(exceptions.PluginNotValidError):
        load_output_plugin(
            plugin_package_directory="tests.data.test_plugins.",
            plugin_package_name="not_a_real_plugin",
        )


# ── Folder validity ──


@dataclass
class FakeFile:
    stem: str
    _is_file: bool

    def is_file(self):
        return self._is_file


@dataclass
class FakeDir:
    _files: list[FakeFile]

    def is_dir(self):
        return True

    def iterdir(self):
        return iter(self._files)


@dataclass
class FakeNonDir:
    def is_dir(self):
        return False


def test_check_folder_validity_with_expected_files():
    """Folder containing __init__.py and main.py should be valid."""
    folder = FakeDir(
        [
            FakeFile("__init__", True),
            FakeFile("main", True),
            FakeFile("utils", True),
        ]
    )
    assert _check_folder_validity(folder) is True


def test_check_folder_validity_missing_main():
    """Folder missing main.py should be invalid."""
    folder = FakeDir([FakeFile("__init__", True)])
    assert _check_folder_validity(folder) is False


def test_check_folder_validity_not_a_directory():
    """Non-directory path should be invalid."""
    assert _check_folder_validity(FakeNonDir()) is False


def test_check_folder_validity_directories_not_counted_as_files():
    """Subdirectories named like expected files should not pass the check."""
    folder = FakeDir(
        [
            FakeFile("__init__", False),  # is_file=False -> it's a subdirectory
            FakeFile("main", True),
        ]
    )
    assert _check_folder_validity(folder) is False


# ── Manager integration ──


def test_get_enabled_plugin_wrappers_empty():
    """Manager with no loaded plugins returns empty enabled list."""
    with patch.object(output_plugin_manager, "find_output_plugins", return_value=[]):
        mgr = output_plugin_manager.OutputPluginManager()
        assert mgr.get_enabled_plugin_wrappers() == []


def test_get_enabled_plugin_wrappers_filters_disabled():
    """Only wrappers with enabled=True should be returned."""
    with patch.object(output_plugin_manager, "find_output_plugins", return_value=[]):
        mgr = output_plugin_manager.OutputPluginManager()

    wrapper_a = MagicMock()
    wrapper_a.enabled = True
    wrapper_b = MagicMock()
    wrapper_b.enabled = False

    mgr.plugin_wrappers = [wrapper_a, wrapper_b]
    assert mgr.get_enabled_plugin_wrappers() == [wrapper_a]
