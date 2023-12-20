"""
Plugin Manager for Joystick Diagrams

Plugin manager serves as the main interface between the GUI and the rest of the application.

- It is responsible for loading and unloading plugins

"""
import logging
import os
from importlib import import_module
from pathlib import Path
from types import ModuleType

import joystick_diagrams.exceptions as JDException

_logger = logging.getLogger(__name__)
PLUGINS_DIRECTORY = "plugins"


class ParserPluginManager:
    def __init__(self):
        self.plugins = self.find_plugins(PLUGINS_DIRECTORY)
        self.loaded_plugins = []

        if self.plugins:
            for plugin in self.plugins:
                try:
                    # Try initiate the plugin
                    self.loaded_plugins.append(self.load_plugin(plugin))
                except JDException.PluginNotValid as e:
                    _logger.error(e)
        else:
            raise JDException.NoPluginsExist()

    def load_plugin(self, module_path: str) -> ModuleType:
        """Attempt to load the plugin"""
        try:
            _logger.debug(f"Loading plugin at module path: {module_path}")
            directory = ".plugins."
            path = os.path.join(directory, module_path)

            return import_module(directory + module_path + ".main", package=__package__).ParserPlugin()
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
