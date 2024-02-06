from dataclasses import dataclass, field
from pathlib import Path

from db import db_plugin_data

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface


@dataclass
class PluginWrapper:

    plugin: PluginInterface
    _enabled: bool = field(init=False)
    plugin_profile_collection: ProfileCollection = field(init=False)

    def __post_init__(self):
        self.plugin_profile_collection = None
        self.setup_plugin()

    def process(self):
        if self.path:
            self.plugin_profile_collection = self.plugin.process()

    def set_path(self, path: Path) -> bool:
        set = self.plugin.set_path(path)
        return set

    def setup_plugin(self):
        """Sets up a pluginf or first use or restores existing state"""

        existing_configuration = self.get_plugin_configuration(self.plugin.name)

        if existing_configuration:
            self.enabled = existing_configuration[1]
        else:
            self.store_plugin_configuration()

        self.plugin.load_settings()

        if self.plugin.path:
            self.set_path(self.plugin.path)

    def get_plugin_configuration(self, plugin_name: str):
        return db_plugin_data.get_plugin_configuration(plugin_name)

    def store_plugin_configuration(self):
        db_plugin_data.add__update_plugin_configuration(self.name, self.enabled)

    @property
    def path(self):
        return self.plugin.path

    @property
    def name(self):
        return self.plugin.name

    @property
    def version(self):
        return self.plugin.version

    @property
    def icon(self):
        return self.plugin.icon

    @property
    def path_type(self):
        return self.plugin.path_type

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value):

        self._enabled = False if isinstance(value, property) else bool(value)

        if self._enabled is True:
            self.process()
        return self.enabled
