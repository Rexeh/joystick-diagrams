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
        self.plugins = self.find_plugins(PLUGINS_DIRECTORY)
        self.loaded_plugins = []

        if self.plugins:
            for plugin in self.plugins:
                try:
                    # Try initiate the plugin
                    loaded = self.load_plugin(plugin)
                    self.validate_plugin(loaded)
                    self.loaded_plugins.append(loaded)

                except (JDException.PluginNotValid, JSONDecodeError, AttributeError, ValidationError) as e:
                    _logger.error(f"Error with Plugin: {plugin} - {e}")

        else:
            raise JDException.NoPluginsExist()

    def validate_plugin(self, plugin: PluginInterface) -> None | ValidationError:
        return plugin.settings.validators.validate_all()

    def load_plugin(self, module_path: str) -> ModuleType:
        """Attempt to load the plugin"""
        try:
            _logger.debug(f"Loading plugin at module path: {module_path}")

            return import_module(PLUGIN_REL_PATH + module_path + ".main", package=__package__).ParserPlugin()
        except TypeError as e:
            _logger.error(f"{e} - {module_path}")
            raise JDException.PluginNotValid(error=e, value=module_path) from e
        except ModuleNotFoundError as e:
            _logger.error(e)
            raise JDException.PluginNotValid(value=module_path, error=e) from e

    def find_plugins(self, directory) -> list:
        """
        Find python modules in given directory

        Returns list of module names
        """
        _folders = [folder for folder in os.listdir(os.path.join(Path(__file__).resolve().parent, directory))]
        _logger.debug(f"Folders detected: {_folders}")

        folders = [
            folder
            for folder in os.listdir(os.path.join(Path(__file__).resolve().parent, directory))
            if os.path.isdir(os.path.join(os.path.join(Path(__file__).resolve().parent, directory, folder)))
            and folder != "__pycache__"
        ]
        return folders


if __name__ == "__main__":
    app = ParserPluginManager()
