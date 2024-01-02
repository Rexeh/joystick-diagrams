"""
Plugin Manager for Joystick Diagrams

Plugin manager serves as the main interface between the GUI and the rest of the application.

- It is responsible for loading and unloading plugins

"""
import logging
import os
from importlib import import_module
from json import JSONDecodeError
from pathlib import Path
from types import ModuleType

import dynaconf
from dynaconf import ValidationError

import joystick_diagrams.exceptions as JDException
from joystick_diagrams.plugins.plugin_interface import PluginInterface

_logger = logging.getLogger(__name__)
PLUGINS_DIRECTORY = "plugins"
PLUGIN_REL_PATH = ".plugins."


class ParserPluginManager:
    def __init__(self):
        self.plugins = find_plugins(PLUGINS_DIRECTORY)
        self.loaded_plugins = []

        if self.plugins:
            for plugin in self.plugins:
                try:
                    # Try initiate the plugin
                    loaded = load_plugin(plugin_package_name=plugin.name)
                    self.validate_plugin(loaded)
                    self.loaded_plugins.append(loaded)

                except (JDException.PluginNotValid, JSONDecodeError, AttributeError, ValidationError) as e:
                    _logger.error(f"Error with Plugin: {plugin} - {e}")

        else:
            raise JDException.NoPluginsExist()

    def validate_plugin(self, plugin: PluginInterface) -> None | ValidationError:
        return plugin.settings.validators.validate_all()


def load_plugin(plugin_package_directory: str = PLUGIN_REL_PATH, plugin_package_name: str = "") -> ModuleType:
    """Attempt to load the plugin"""
    try:
        _logger.debug(f"Loading plugin at module path: {plugin_package_name}")

        return import_module(
            f"{plugin_package_directory}{plugin_package_name}.main", package=__package__
        ).ParserPlugin()
    except TypeError as e:
        _logger.error(f"{e} - {plugin_package_name}")
        raise JDException.PluginNotValid(error=e, value=plugin_package_name) from e
    except ModuleNotFoundError as e:
        _logger.error(e)
        raise JDException.PluginNotValid(value=plugin_package_name, error=e) from e


def find_plugins(directory) -> list[Path]:
    """
    Find python modules in given directory

    Returns list of module names

    """
    _expected_files = ["__init__.py", "config.py", "main.py", "settings.json"]
    _folders = [folder for folder in Path(os.path.join(Path(__file__).resolve().parent, directory)).iterdir()]
    _logger.debug(f"Folders detected: {_folders}")

    def _check_expected_files(directory: Path):
        directory_files = [f.name for f in directory.iterdir() if f.is_file()]

        for _file in _expected_files:
            if _file not in directory_files:
                return False

        return True

    def _check_folder_validity(folder: Path):
        if folder.is_dir() and _check_expected_files(folder):
            return True

        return False

    folders = [folder for folder in _folders if _check_folder_validity(folder) and folder.name != "__pycache__"]
    return folders


if __name__ == "__main__":
    app = ParserPluginManager()
    print(app)
