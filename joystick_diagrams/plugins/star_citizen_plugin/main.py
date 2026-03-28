from pathlib import Path

from pydantic import Field

from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings
from joystick_diagrams.plugins.star_citizen_plugin.star_citizen import StarCitizen


class StarCitizenSettings(PluginSettings):
    actionmaps_file: Path | None = Field(
        default=None,
        title="actionmaps.xml",
        json_schema_extra={
            "is_folder": False,
            "default_path": "~/",
            "extensions": [".xml"],
        },
    )


class ParserPlugin(PluginInterface):
    plugin_meta = PluginMeta(
        name="Star Citizen", version="2.0.0", icon_path="img/sc.png"
    )
    plugin_settings_model = StarCitizenSettings

    def __init__(self):
        super().__init__()
        self.instance: StarCitizen | None = None

    def process(self):
        if self.instance:
            return self.instance.parse()
        return None

    def _rebuild_instance(self) -> None:
        actionmaps_file = self.get_setting("actionmaps_file")
        if actionmaps_file and Path(actionmaps_file).exists():
            self.instance = StarCitizen(actionmaps_file)
        else:
            self.instance = None

    def update_setting(self, key: str, value) -> None:
        super().update_setting(key, value)
        self._rebuild_instance()

    def on_settings_loaded(self) -> None:
        self._rebuild_instance()


if __name__ == "__main__":
    plugin = ParserPlugin()
