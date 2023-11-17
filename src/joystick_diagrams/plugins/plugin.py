from dataclasses import dataclass
from joystick_diagrams.plugins.plugin_interface import PluginInterface


@dataclass
class Plugin:
    name: PluginInterface

    def __post_init__(self):
        print(self._get_plugin_metadata())

    def _get_plugin_metadata(self):
        return self.name.name()
