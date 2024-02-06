import json
import logging
from pathlib import Path

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.dcs_world_plugin.dcs_world import DCSWorldParser
from joystick_diagrams.plugins.plugin_interface import PluginInterface

from .config import settings

_logger = logging.getLogger("__name__")

CONFIG_FILE = "data.json"


class ParserPlugin(PluginInterface):
    def __init__(self):
        super().__init__()
        self.settings = settings
        self.settings.validators.register()
        self.path = None
        self.instance: DCSWorldParser = None

    def process(self) -> ProfileCollection:
        return self.instance.process_profiles()

    def set_path(self, path: Path) -> bool:
        try:
            self.instance = DCSWorldParser(path)
            self.path = path
            self.save_plugin_state()

        except Exception as e:
            return False

        return True

    def save_plugin_state(self):
        with open(Path.joinpath(Path(__file__).parent, CONFIG_FILE), "w", encoding="UTF8") as f:
            f.write(json.dumps({"path": self.path.__str__()}))

    def load_settings(self) -> None:
        try:
            with open(Path.joinpath(Path(__file__).parent, CONFIG_FILE), "r", encoding="UTF8") as f:
                data = json.loads(f.read())
                self.path = Path(data["path"]) if data["path"] else None
        except FileNotFoundError:
            pass

    @property
    def path_type(self):
        return self.FolderPath("Select your DCS World directory", "\\%%USERPROFILE%%\\Saved Games")

    @property
    def icon(self):
        return f"{Path.joinpath(Path(__file__).parent,self.settings.PLUGIN_ICON)}"


if __name__ == "__main__":
    plugin = ParserPlugin()
