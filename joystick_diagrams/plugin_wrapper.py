""" Wrapper functionality for Plugins for the UI

Primarily handles passthrough plugin_interface concrete implementations.
"""

import logging
from dataclasses import dataclass, field

from joystick_diagrams.db import db_plugin_data
from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginSettings

_logger = logging.getLogger(__name__)


@dataclass
class PluginWrapper:
    plugin: PluginInterface
    _enabled: bool = False
    _error: str = field(default_factory=str)
    plugin_profile_collection: ProfileCollection | None = field(init=False)

    def __post_init__(self):
        self.plugin_profile_collection = None
        self.setup_plugin()

    def process(self) -> bool:
        """Runs a specific plugin, attaching the result to the wrapper."""
        self.plugin_profile_collection = None
        try:
            if self.ready and self.enabled:
                result = self.plugin.process()
                if isinstance(result, ProfileCollection):
                    self.plugin_profile_collection = result
            return True
        except Exception as e:
            _logger.error(JoystickDiagramsError(f"Plugin had an unexpected error: {e}"))
            self.push_error(
                str(JoystickDiagramsError(f"Plugin had an unexpected error: {e}"))
            )
            return False

    def push_error(self, error: str):
        self._error = error

    def disable_plugin(self):
        self._error = "Plugin is disabled"

    def enable_plugin(self):
        self._error = ""

    def setup_plugin(self):
        """Loads saved settings and restores enabled state from the database."""
        try:
            self.plugin.load_settings()

            existing_configuration = self.get_plugin_configuration(self.plugin.name)
            if existing_configuration:
                # Set _enabled directly to avoid triggering enable/disable side effects
                self._enabled = bool(existing_configuration[1])
            else:
                self.store_plugin_configuration()

        except PermissionError as e:
            _logger.error(
                f"Permission error during plugin setup for {self.plugin.name}: {e}"
            )
            self.push_error(str(e))
        except JoystickDiagramsError as e:
            _logger.error(e)

    @property
    def ready(self) -> bool:
        """Delegates to the plugin's own ready property (based on required Path fields)."""
        return self.plugin.ready

    @property
    def error(self) -> str:
        return self._error

    @error.setter
    def error(self, value: str):
        self._error = value

    def get_plugin_configuration(self, plugin_name: str):
        return db_plugin_data.get_plugin_configuration(plugin_name)

    def store_plugin_configuration(self):
        db_plugin_data.add__update_plugin_configuration(self.name, self.enabled)

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
    def plugin_settings(self) -> PluginSettings | None:
        return self.plugin._plugin_settings

    def has_settings(self) -> bool:
        return self.plugin._plugin_settings is not None

    def update_setting(self, key: str, value) -> None:
        self.plugin.update_setting(key, value)

    @property
    def enabled(self) -> bool:
        return bool(self._enabled)

    @enabled.setter
    def enabled(self, value):
        self._enabled = False if isinstance(value, property) else bool(value)

        if self._enabled:
            self.enable_plugin()
        else:
            self.disable_plugin()

        self.store_plugin_configuration()
