from pathlib import Path

from pydantic import Field

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.fs2020_plugin.ms_flight_simulator import FS2020Parser
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings


class FS2020Settings(PluginSettings):
    game_dir: Path | None = Field(
        default=None,
        title="Flight Simulator 2020 Folder",
        json_schema_extra={
            "is_folder": True,
            "default_path": "~/AppData",
        },
    )


class ParserPlugin(PluginInterface):
    plugin_meta = PluginMeta(
        name="Flight Simulator 2020", version="0.0.1", icon_path="img/icon.png"
    )
    plugin_settings_model = FS2020Settings

    def __init__(self):
        super().__init__()
        self.instance: FS2020Parser | None = None

    def process(self) -> ProfileCollection:
        if self.instance:
            return self.instance.run()
        return ProfileCollection()

    def _rebuild_instance(self) -> None:
        game_dir = self.get_setting("game_dir")
        if game_dir and Path(game_dir).exists():
            self.instance = FS2020Parser(game_dir)
        else:
            self.instance = None

    def update_setting(self, key: str, value) -> None:
        super().update_setting(key, value)
        self._rebuild_instance()

    def on_settings_loaded(self) -> None:
        self._rebuild_instance()


if __name__ == "__main__":
    pass
