import json
import logging
from pathlib import Path

from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.star_citizen_plugin.config import (
    settings,  # TODO Move out plugins to separate package
)
from joystick_diagrams.plugins.star_citizen_plugin.star_citizen import (
    StarCitizen,  # TODO Move out plugins to separate package
)

CONFIG_FILE = "data.json"
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
            self.instance = inst
            self.path = path
            self.save_plugin_state()
            return True

        return False

    def save_plugin_state(self):
        with open(
            Path.joinpath(self.get_plugin_data_path(), CONFIG_FILE),
            "w",
            encoding="UTF8",
        ) as f:
            f.write(json.dumps({"path": str(self.path)}))

    def load_settings(self) -> None:
        try:
            with open(
                Path.joinpath(self.get_plugin_data_path(), CONFIG_FILE),
                "r",
                encoding="UTF8",
            ) as f:
                data = json.loads(f.read())
                self.path = Path(data["path"]) if data["path"] else None
        except FileNotFoundError:
            pass

    @property
    def path_type(self):
        return self.FilePath(
            "Select your Star Citizen actionmaps.xml",
            Path.home(),
            [".xml"],
        )

    @property
    def icon(self):
        return f"{Path.joinpath(Path(__file__).parent,self.settings.PLUGIN_ICON)}"


if __name__ == "__main__":
    plugin = ParserPlugin()
