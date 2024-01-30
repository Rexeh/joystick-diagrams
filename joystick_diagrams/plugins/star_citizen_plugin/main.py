import logging
from pathlib import Path

from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.star_citizen_plugin.config import (
    settings,  # TODO Move out plugins to separate package
)
from joystick_diagrams.plugins.star_citizen_plugin.star_citizen import (
    StarCitizen,  # TODO Move out plugins to separate package
)

_logger = logging.getLogger("__name__")


class ParserPlugin(PluginInterface):
    def __init__(self):
        self.path = None
        self.settings = settings
        self.settings.validators.register()
        self.instance: StarCitizen = None

    def process(self):
        return self.instance.parse()

    def set_path(self, path: Path) -> bool:
        inst = StarCitizen(path)

        if inst:
            self.path = path
            self.instance = inst
            return True

        return False

    def load_settings(self) -> None:
        pass

    @property
    def path_type(self):
        return self.FilePath("Select your Star Citizen actionmaps.xml", "/%USERPROFILE%/Saved Games", [".xml"])

    @property
    def icon(self):
        return f"{Path.joinpath(Path(__file__).parent,self.settings.PLUGIN_ICON)}"


if __name__ == "__main__":
    plugin = ParserPlugin()
