from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginMeta


class ParserPlugin(PluginInterface):
    plugin_meta = PluginMeta(
        name="Example Test Plugin", version="0.0.1", icon_path="img/logo.ico"
    )

    def __init__(self):
        super().__init__()

    def process(self) -> ProfileCollection:
        return ProfileCollection()


if __name__ == "__main__":
    plugin = ParserPlugin()
