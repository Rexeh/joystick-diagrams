"""
Plugin Manager for Joystick Diagrams

Plugin manager serves as the main interface between the GUI and the rest of the application.

- It is responsible for loading and unloading plugins

"""
from importlib import import_module
from pathlib import Path
import os
from types import ModuleType
import joystick_diagrams.exceptions as exp
from joystick_diagrams.plugins.plugin import Plugin
import logging

_logger = logging.getLogger(__name__)


class ParserPluginManager:
    def __init__(self):
        plugins = self.find_plugins()
        self._plugins = []
        self._available = []

        if plugins != []:
            for plugin in plugins:
                try:
                    # Try initiate the plugin
                    self._plugins.append(self.load_plugin(plugin))
                except exp.plugin_not_valid as e:
                    _logger.error(e)
        else:
            raise exp.no_plugins_exist()

    def load_plugin(self, module_path: str) -> ModuleType:
        """Attempt to load the plugin"""
        try:
            # Todo make nicer the joining of relative pathing...
            return import_module("." + module_path + ".main", "joystick_diagrams.plugins").CustomPlugin()
        except TypeError as e:
            raise exp.plugin_not_valid(error=e) from e
        except ModuleNotFoundError as e:
            raise exp.plugin_not_valid(value=module_path, error=e) from e

    def find_plugins(self, directory="plugins") -> list:
        """
        Find python modules in given directory

        Returns list of module names
        """
        folders = [
            folder
            for folder in os.listdir(os.path.join(Path(__file__).resolve().parent, directory))
            if os.path.isdir(os.path.join(os.path.join(Path(__file__).resolve().parent, directory, folder)))
            and folder != "__pycache__"
        ]
        return folders

    def run(self):
        for plugin in self._plugins:
            self._available.append(Plugin(plugin))

        print(self._available)


if __name__ == "__main__":
    # We are going to create an instance of our application
    app = ParserPluginManager()
    # We are going to run it
    app.run()
    print(app._available[0].name.version())
    print()
