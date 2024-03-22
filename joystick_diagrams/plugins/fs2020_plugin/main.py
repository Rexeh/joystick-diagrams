import logging
from pathlib import Path

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface

from .config import settings

_logger = logging.getLogger("__name__")


class ParserPlugin(PluginInterface):
    def __init__(self):
        super().__init__()
        self.settings = settings
        self.settings.validators.register()
        self.path = None

    def process(self) -> ProfileCollection:
        # Process your plugin, to build and return a profile collection instance
        return ProfileCollection()

    def set_path(self, path: Path) -> bool:
        try:
            # Handle the Path provided
            # Validate the path / file/ folder provided is suitable for your plugin
            # Pre-initialise any instances if required
            pass

        except Exception:
            return False

        return True

    def save_plugin_state(self):
        # Persist any data changes when they are modified
        # self.get_plugin_data_path() - Gets your plugins app data path automatically
        pass

    def load_settings(self) -> None:
        # Load any data / initialise your plugin - Automatically called on start up if plugin is enabled
        pass

    @property
    def path_type(self):
        return self.FolderPath(
            "This title shows up on the UI select dialog",
            Path.joinpath(Path.home(), "Saved Games"),
        )

    @property
    def icon(self):
        return f"{Path.joinpath(Path(__file__).parent,self.settings.PLUGIN_ICON)}"


if __name__ == "__main__":
    pass
