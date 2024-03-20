import logging
from pathlib import Path

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.xr_neck_safer_plugin import config
from joystick_diagrams.plugins.xr_neck_safer_plugin.xr_neck_safer import XRNeckSafer

_logger = logging.getLogger("__name__")


class ParserPlugin(PluginInterface):
    def __init__(self):
        super().__init__()
        self.settings = config.settings
        self.settings.validators.register()
        self.path = None

    def process(self) -> ProfileCollection:
        return self.instance.process_file()

    def set_path(self, path: Path) -> bool:
        try:
            path_set = XRNeckSafer(path)

            if path_set:
                self.path = path
                self.instance = path_set

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
        return self.FilePath(
            "This title shows up on the UI select dialog",
            Path.joinpath(Path.home(), "Saved Games"),
            [".cfg"],
        )

    @property
    def icon(self):
        return f"{Path.joinpath(Path(__file__).parent,self.settings.PLUGIN_ICON)}"


if __name__ == "__main__":
    pp = ParserPlugin()

    pp.process()
