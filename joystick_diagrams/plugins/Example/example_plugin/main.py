from pathlib import Path

from pydantic import Field

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings


class ExampleSettings(PluginSettings):
    # Define your path fields here. Required paths block ready state until set.
    source_dir: Path | None = Field(
        default=None,
        title="Source Folder",
        json_schema_extra={
            "is_folder": True,
            "default_path": "~/Saved Games",
        },
    )
    # Add any non-path settings below:
    # some_toggle: bool = Field(default=True, title="Enable Feature")


class ParserPlugin(PluginInterface):
    plugin_meta = PluginMeta(
        name="EXAMPLE PLUGIN", version="0.0.1", icon_path="img/logo.ico"
    )
    plugin_settings_model = ExampleSettings

    def __init__(self):
        super().__init__()

    def process(self) -> ProfileCollection:
        # Process your plugin, to build and return a profile collection instance
        return ProfileCollection()

    def on_settings_loaded(self) -> None:
        # Rebuild any internal state from self.get_setting(...) here
        pass


if __name__ == "__main__":
    pass
