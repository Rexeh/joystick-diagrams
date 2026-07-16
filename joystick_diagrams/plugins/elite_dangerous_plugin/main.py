from pathlib import Path

from pydantic import Field

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings

from .elite_dangerous import EliteDangerous


class EliteDangerousSettings(PluginSettings):
    binds_file: Path | None = Field(
        default=None,
        title="Elite Dangerous .binds File",
        json_schema_extra={
            "is_folder": False,
            "default_path": "~/AppData/Local/Frontier Developments/Elite Dangerous/Options/Bindings",
            "extensions": [".binds"],
        },
    )


class ParserPlugin(PluginInterface):
    plugin_meta = PluginMeta(
        name="Elite Dangerous",
        version="0.0.1",
        icon_path="img/ed.ico",
    )
    plugin_settings_model = EliteDangerousSettings

    def __init__(self):
        super().__init__()
        self.instance: EliteDangerous | None = None

    def process(self) -> ProfileCollection:
        if self.instance:
            return self.instance.parse()
        return ProfileCollection()

    def _rebuild_instance(self) -> None:
        binds_file = self.get_setting("binds_file")
        if binds_file and Path(binds_file).exists():
            self.instance = EliteDangerous(binds_file)
        else:
            self.instance = None

    def update_setting(self, key, value) -> None:
        super().update_setting(key, value)
        self._rebuild_instance()

    def on_settings_loaded(self) -> None:
        self._rebuild_instance()


if __name__ == "__main__":
    pass
