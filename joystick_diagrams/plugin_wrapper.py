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
    _enabled: bool = False
    ready: bool = False
    plugin_profile_collection: ProfileCollection | None = field(init=False)
    error: str = field(default_factory=str)

    def __post_init__(self):
        self.plugin_profile_collection = None
        self.setup_plugin()

    # @handle_bare_exception
    def process(self) -> bool:
        """Runs a specific plugin, attaching the result to the wrapper"""
        self.plugin_profile_collection = None
        try:
            if self.path and self.enabled:
                result = self.plugin.process()

                if isinstance(result, ProfileCollection):
                    self.plugin_profile_collection = result

            return True

        except Exception as e:  # Base exception handling as cannot garantee plugin conformance to handle errors
            _logger.error(JoystickDiagramsError(f"Plugin had an unexpected error: {e}"))
            self.push_error(
                str(JoystickDiagramsError(f"Plugin had an unexpected error: {e}"))
            )
            return False

    def push_error(self, error: str):
        self.error = ""
        self.error = error

    # @handle_bare_exception
    def set_path(self, path: Path) -> bool:
        """Sets the path for a given plugin"""
        try:
            path_set = self.plugin.set_path(path)
            self.set_ready(path_set)
            return path_set
        except JoystickDiagramsError as e:
            _logger.error(e)
            self.set_ready(False)
            self.push_error(str(e))

        return False

    def disable_plugin(self):
        self.errors = ""
        self.ready = False
        self.push_error("Plugin is disabled")

    def enable_plugin(self):
        self.setup_plugin_path()

    # @handle_bare_exception
    def setup_plugin(self):
        """Sets up a pluging on first use or restores existing state"""

        try:
            # Load the plugins own settings
            self.plugin.load_settings()

            if not self.plugin.path:
                self.push_error("Plugin has not been setup")
            # Call the set_path to initialise the plugin correctly
            self.setup_plugin_path()

            # Retrieve stored state for the PluginWrapper
            existing_configuration = self.get_plugin_configuration(self.plugin.name)

            if existing_configuration:
                self.enabled = existing_configuration[1]
            else:
                self.store_plugin_configuration()

        except JoystickDiagramsError as e:
            _logger.error(e)

    def setup_plugin_path(self):
        if self.plugin.path:
            path_set = self.set_path(self.plugin.path)
            self.set_ready(path_set)

    def set_ready(self, state: bool):
        self.ready = True if state else False

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
        return bool(self._enabled)

    @enabled.setter
    def enabled(self, value):
        self._enabled = False if isinstance(value, property) else bool(value)

        if self._enabled is True:
            self.enable_plugin()

        if self._enabled is False:
            self.disable_plugin()

        self.store_plugin_configuration()
        return self.enabled
