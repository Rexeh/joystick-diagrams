from dataclasses import dataclass

import pytest

from joystick_diagrams import exceptions, plugin_manager
from joystick_diagrams.plugin_manager import (
    check_expected_files,
    check_folder_validity,
    load_plugin,
)

TEST_PLUGIN_PATH = "../tests/data/test_plugins"


def test_load_plugin_not_valid(caplog):
    plugin_package = "tests.data.test_plugins."
    module_path = "notPlugin"

    with pytest.raises(exceptions.PluginNotValid) as e:
        load_plugin(plugin_package, module_path)

    assert "notPlugin.main" in caplog.text


@pytest.fixture
def plugin_path_directory(request):
    """Used to provide fixtures for Pathlib

    Accepts FileNames, is_File and is_Dir checks per item
    """

    @dataclass
    class PathItem:
        stem: str
        file: bool

        def is_file(self):
            return self.file if self.file else False

        def is_dir(self):
            return self.file if not self.file else True

    @dataclass
    class MockPathObject:
        items: set[PathItem]

        def iterdir(self):
            for i in self.items:
                yield i

    path_items = [PathItem(x, request.param.get(x)) for x in request.param]
    return MockPathObject(path_items)


@pytest.mark.parametrize("plugin_path_directory", [{"FileA": True, "FileB": True, "FolderC": False}], indirect=True)
def test_check_expected_files_valid(monkeypatch, plugin_path_directory):
    _expected_files = ["FileA", "FileB"]
    monkeypatch.setattr(plugin_manager, "EXPECTED_PLUGIN_FILES", _expected_files)

    _mock_path = plugin_path_directory
    _check = check_expected_files(_mock_path)

    assert _check is True


@pytest.mark.parametrize("plugin_path_directory", [{"FileA": True, "FileB": True, "FileC": False}], indirect=True)
def test_check_expected_files_invalid(monkeypatch, plugin_path_directory):
    _expected_files = ["FileC", "FileD"]
    monkeypatch.setattr(plugin_manager, "EXPECTED_PLUGIN_FILES", _expected_files)

    _mock_path = plugin_path_directory
    _check = check_expected_files(_mock_path)

    assert _check is False


@pytest.mark.parametrize("plugin_path_directory", [{"Folder": True}], indirect=True)
def test_check_folder_validity_valid(monkeypatch, plugin_path_directory):
    def mock_check_files(monkeypatch):
        return True

    monkeypatch.setattr(plugin_manager, "check_expected_files", mock_check_files)

    _check = check_folder_validity(plugin_path_directory.items[0])

    assert _check is True


@pytest.mark.parametrize("plugin_path_directory", [{"Folder": False}], indirect=True)
def test_check_folder_validity_invalid(monkeypatch, plugin_path_directory):
    def mock_check_files(monkeypatch):
        return True

    monkeypatch.setattr(plugin_manager, "check_expected_files", mock_check_files)

    _check = check_folder_validity(plugin_path_directory.items[0])

    assert _check is False
