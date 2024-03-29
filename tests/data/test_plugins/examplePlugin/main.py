import logging
from pathlib import Path

from joystick_diagrams.plugins.plugin_interface import PluginInterface

from .config import settings

_logger = logging.getLogger("__name__")


class ParserPlugin(PluginInterface):
    def __init__(self):
        self.path = None
        self.settings = settings
        self.settings.validators.register()

    def process(self):
        return None

    def set_path(self, path: Path) -> bool:
        self.path = path
        return True

    def load_settings(self) -> None:
        pass

    @property
    def path_type(self):
        return self.FolderPath(
            "Select your DCS World directory", "\\%%USERPROFILE%%\\Saved Games"
        )

    @property
    def icon(self) -> str:
        return f"{Path.joinpath(Path(__file__).parent,self.settings.PLUGIN_ICON)}"


if __name__ == "__main__":
    plugin = ParserPlugin()
