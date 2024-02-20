""" Wrapper functionality for Plugins for the UI

Primarily handles passthrough plugin_interface concrete implementations.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from joystick_diagrams.db import db_plugin_data
from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface

_logger = logging.getLogger(__name__)


@dataclass
class PluginWrapper:
    plugin: PluginInterface
    _enabled: bool = field(init=False)
    plugin_profile_collection: ProfileCollection = field(init=False)

    def __post_init__(self):
        self.plugin_profile_collection = None
        self._enabled = False
        self.ready = False
        self.setup_plugin()

    # @handle_bare_exception
    def process(self):
        """Runs a specific plugin, attaching the result to the wrapper"""
        try:
            if self.path:
                result = self.plugin.process()

                if isinstance(result, ProfileCollection):
                    self.plugin_profile_collection = result

        except JoystickDiagramsError as e:
            _logger.error(e)

    # @handle_bare_exception
    def set_path(self, path: Path) -> bool:
        """Sets the path for a given plugin"""
        try:
            path_set = self.plugin.set_path(path)
            self.ready = True if path_set else False
            return self.ready
        except JoystickDiagramsError as e:
            _logger.error(e)

        return False

    # @handle_bare_exception
    def setup_plugin(self):
        """Sets up a pluging on first use or restores existing state"""

        try:
            # Load the plugins own settings
            self.plugin.load_settings()

            # Call the set_path to initialise the plugin correctly
            if self.plugin.path:
                path_set = self.set_path(self.plugin.path)
                self.ready = True if path_set else False

            # Retrieve stored state for the PluginWrapper
            existing_configuration = self.get_plugin_configuration(self.plugin.name)

            if existing_configuration:
                self.enabled = existing_configuration[1]
            else:
                self.store_plugin_configuration()

        except JoystickDiagramsError as e:
            _logger.error(e)

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
        # TODO process the plugins syncronously on enable
        # if self._enabled is True:
        #    self.process()
        return self.enabled
