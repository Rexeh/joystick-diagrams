"""Wrapper functionality for Output Plugins."""

import logging
from dataclasses import dataclass, field

from joystick_diagrams.db import db_plugin_data
from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.plugins.output_plugin_interface import (
    ExportResult,
    OutputPluginInterface,
)
from joystick_diagrams.plugins.plugin_settings import PluginSettings

_logger = logging.getLogger(__name__)

# Prefix to namespace output plugin DB entries separately from input plugins
_DB_PREFIX = "output:"


@dataclass
class OutputPluginWrapper:
    plugin: OutputPluginInterface
    _enabled: bool = False
    _error: str = field(default_factory=str)

    def __post_init__(self):
        self.setup_plugin()

    def run(self, results: list[ExportResult]) -> bool:
        """Runs the output plugin with the given export results."""
        if not self.ready or not self.enabled:
            return True
        try:
            return self.plugin.process_export(results)
        except Exception as e:
            _logger.error(
                JoystickDiagramsError(f"Output plugin had an unexpected error: {e}")
            )
            self._error = str(e)
            return False

    def setup_plugin(self):
        """Loads saved settings and restores enabled state from the database."""
        try:
            self.plugin.load_settings()
            existing_configuration = self.get_plugin_configuration(self._db_key)
            if existing_configuration:
                self._enabled = bool(existing_configuration[1])
            else:
                self.store_plugin_configuration()
        except PermissionError as e:
            _logger.error(
                f"Permission error during output plugin setup for {self.plugin.name}: {e}"
            )
            self._error = str(e)
        except JoystickDiagramsError as e:
            _logger.error(e)

    @property
    def _db_key(self) -> str:
        return f"{_DB_PREFIX}{self.plugin.name}"

    @property
    def ready(self) -> bool:
        return self.plugin.ready

    @property
    def error(self) -> str:
        return self._error

    def get_plugin_configuration(self, plugin_name: str):
        return db_plugin_data.get_plugin_configuration(plugin_name)

    def store_plugin_configuration(self):
        db_plugin_data.add__update_plugin_configuration(self._db_key, self.enabled)

    @property
    def name(self) -> str:
        return self.plugin.name

    @property
    def version(self) -> str:
        return self.plugin.version

    @property
    def icon(self) -> str:
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
        self.store_plugin_configuration()
