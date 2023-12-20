import logging
from pathlib import Path

from joystick_diagrams.plugins.plugin_interface import PluginInterface

from .config import settings

PLUGIN_NAME = "Star Citizen"
PLUGIN_ICON = "img/logo.ico"
VERSION = "0.0.1"

_logger = logging.getLogger("__name__")


class ParserPlugin(PluginInterface):
    def __init__(self):
        self.path = None
        self.settings = settings

    def process(self):
        return None

    def set_path(self, path: Path) -> bool:
        self.path = path
        return True

    @property
    def name(self) -> str:
        return f"{PLUGIN_NAME}"

    @property
    def version(self) -> str:
        return f"{VERSION}"

    @property
    def icon(self) -> str:
        return f"{Path.joinpath(Path(__file__).parent,PLUGIN_ICON)}"

    @property
    def get_path(self) -> bool:
        return self.path
