import logging
from pathlib import Path

from pydantic import Field

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings

from .il2_parser import IL2Parser

_logger = logging.getLogger(__name__)


class IL2Settings(PluginSettings):
    input_dir: Path | None = Field(
        default=None,
        title="IL-2 Input Directory",
        description="Directory containing global.actions and devices.txt",
        json_schema_extra={
            "is_folder": True,
            "default_path": r"C:\Program Files\IL-2 Sturmovik Great Battles\data\input",
        },
    )


class ParserPlugin(PluginInterface):
    plugin_meta = PluginMeta(
        name="IL-2 Sturmovik", version="1.0.0", icon_path="img/icon.png"
    )
    plugin_settings_model = IL2Settings

    def __init__(self):
        super().__init__()
        self.instance: IL2Parser | None = None

    def process(self) -> ProfileCollection:
        if self.instance:
            return self.instance.process_profiles()
        return ProfileCollection()

    def _rebuild_instance(self) -> None:
        input_dir = self.get_setting("input_dir")
        if input_dir and Path(input_dir).exists():
            global_actions = Path(input_dir) / "global.actions"
            devices_file = Path(input_dir) / "devices.txt"
            if global_actions.exists() and devices_file.exists():
                self.instance = IL2Parser(input_dir)
                return
        self.instance = None

    def update_setting(self, key: str, value) -> None:
        super().update_setting(key, value)
        self._rebuild_instance()

    def on_settings_loaded(self) -> None:
        self._rebuild_instance()


if __name__ == "__main__":
    plugin = ParserPlugin()
