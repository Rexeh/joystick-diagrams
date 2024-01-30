from dataclasses import dataclass, field
from pathlib import Path

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface


@dataclass
class PluginWrapper:
    plugin_name: str
    plugin_version: str
    plugin_icon: Path
    plugin: PluginInterface
    plugin_profile_collection: ProfileCollection = field(init=False)
    enabled: bool

    def __post_init__(self):
        self.plugin_profile_collection = None
