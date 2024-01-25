import logging
from pathlib import Path

from joystick_diagrams.plugins.joystick_gremlin_plugin.joystick_gremlin import (
    JoystickGremlinParser,
)
from joystick_diagrams.plugins.plugin_interface import PluginInterface

from .config import settings

_logger = logging.getLogger("__name__")


class ParserPlugin(PluginInterface):
    def __init__(self):
        self.path = None
        self.settings = settings
        self.settings.validators.register()
        self.instance: JoystickGremlinParser = None

    def process(self):
        return self.instance.create_dictionary()

    def set_path(self, path: Path) -> bool:
        inst = JoystickGremlinParser(path)

        if inst:
            self.instance = inst
            self.path = path
            return True

        return False

    @property
    def path_type(self):
        return self.FilePath("Select your Joystick Gremlin .XML file", "/%USERPROFILE%/Saved Games", [".xml"])

    @property
    def name(self) -> str:
        return f"{self.settings.PLUGIN_NAME}"

    @property
    def version(self) -> str:
        return f"{self.settings.VERSION}"

    @property
    def icon(self) -> str:
        return f"{Path.joinpath(Path(__file__).parent,self.settings.PLUGIN_ICON)}"

    @property
    def get_path(self) -> bool:
        return self.path


if __name__ == "__main__":
    plugin = ParserPlugin()
    print(plugin)
