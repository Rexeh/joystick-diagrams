from pathlib import Path

from pydantic import Field

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.dcs_world_plugin.dcs_world import DCSWorldParser
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings


class DCSSettings(PluginSettings):
    game_dir: Path | None = Field(
        default=None,
        title="DCS World Folder",
        json_schema_extra={
            "is_folder": True,
            "default_path": "~/Saved Games",
        },
    )
    remove_easy_modes: bool = Field(
        default=True,
        title="Remove Easy Mode Profiles",
        description="Hides aircraft variants whose profile name ends with '_easy' (e.g. A-10A_easy). Requires re-running plugins to take effect.",
    )


class ParserPlugin(PluginInterface):
    plugin_meta = PluginMeta(name="DCS World", version="2.0.0", icon_path="img/dcs.ico")
    plugin_settings_model = DCSSettings

    def __init__(self):
        super().__init__()
        self.instance: DCSWorldParser | None = None

    def process(self) -> ProfileCollection:
        if self.instance:
            return self.instance.process_profiles()
        return ProfileCollection()

    def _rebuild_instance(self) -> None:
        game_dir = self.get_setting("game_dir")
        if game_dir and Path(game_dir).exists():
            self.instance = DCSWorldParser(
                game_dir, easy_modes=self.get_setting("remove_easy_modes")
            )
        else:
            self.instance = None

    def update_setting(self, key: str, value) -> None:
        super().update_setting(key, value)
        self._rebuild_instance()

    def on_settings_loaded(self) -> None:
        self._rebuild_instance()


if __name__ == "__main__":
    plugin = ParserPlugin()
