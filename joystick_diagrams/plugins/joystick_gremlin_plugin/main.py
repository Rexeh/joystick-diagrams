from pathlib import Path

from pydantic import Field

from joystick_diagrams.plugins.joystick_gremlin_plugin.joystick_gremlin import (
    JoystickGremlinParser,
)
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings


class JoystickGremlinSettings(PluginSettings):
    profile_file: Path | None = Field(
        default=None,
        title="Joystick Gremlin Profile",
        json_schema_extra={
            "is_folder": False,
            "default_path": "~/",
            "extensions": [".xml"],
        },
    )


class ParserPlugin(PluginInterface):
    plugin_meta = PluginMeta(
        name="Joystick Gremlin (2.7X)", version="2.0.0", icon_path="img/jg.ico"
    )
    plugin_settings_model = JoystickGremlinSettings

    def __init__(self):
        super().__init__()
        self.instance: JoystickGremlinParser | None = None

    def process(self):
        if self.instance:
            return self.instance.create_dictionary()
        return None

    def _rebuild_instance(self) -> None:
        profile_file = self.get_setting("profile_file")
        if profile_file and Path(profile_file).exists():
            self.instance = JoystickGremlinParser(profile_file)
        else:
            self.instance = None

    def update_setting(self, key: str, value) -> None:
        super().update_setting(key, value)
        self._rebuild_instance()

    def on_settings_loaded(self) -> None:
        self._rebuild_instance()


if __name__ == "__main__":
    pass
