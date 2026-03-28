import inspect
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from joystick_diagrams import utils
from joystick_diagrams.exceptions import (
    DirectoryNotValidError,
    FileNotValidError,
    FileTypeInvalidError,
)
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings

_logger = logging.getLogger(__name__)


class PluginInterface(ABC):
    plugin_meta: ClassVar[PluginMeta]
    plugin_settings_model: ClassVar[type[PluginSettings] | None] = None

    def __init__(self):
        if not isinstance(getattr(type(self), "plugin_meta", None), PluginMeta):
            raise TypeError(
                f"Plugin {type(self).__name__} must define "
                "`plugin_meta = PluginMeta(name=..., version=..., icon_path=...)`"
            )
        self._plugin_settings: PluginSettings | None = (
            self.plugin_settings_model() if self.plugin_settings_model else None
        )

    # ------------------------------------------------------------------
    # Abstract interface — plugins must implement process()
    # ------------------------------------------------------------------

    @abstractmethod
    def process(self) -> ProfileCollection:
        """Runs the plugin and returns a ProfileCollection."""
        ...

    # ------------------------------------------------------------------
    # Concrete metadata properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self.plugin_meta.name

    @property
    def version(self) -> str:
        return self.plugin_meta.version

    @property
    def icon(self) -> str:
        """Resolves icon_path relative to the concrete plugin's own directory."""
        plugin_dir = Path(inspect.getfile(type(self))).parent
        return str(plugin_dir / self.plugin_meta.icon_path)

    # ------------------------------------------------------------------
    # Ready state — True when all required Path fields are set
    # ------------------------------------------------------------------

    @property
    def ready(self) -> bool:
        """True when all required path fields in plugin_settings have been set."""
        if self._plugin_settings is None:
            return True  # no configuration required
        for field_name, field_info in type(self._plugin_settings).model_fields.items():
            annotation = field_info.annotation
            is_path = annotation is Path or (
                hasattr(annotation, "__args__") and Path in annotation.__args__
            )
            if not is_path:
                continue
            extra = field_info.json_schema_extra or {}
            if extra.get("required", True):  # path fields are required by default
                if getattr(self._plugin_settings, field_name) is None:
                    return False
        return True

    # ------------------------------------------------------------------
    # Settings access helpers
    # ------------------------------------------------------------------

    def get_setting(self, key: str):
        """Get a plugin setting value by field name."""
        if self._plugin_settings is None:
            return None
        return getattr(self._plugin_settings, key, None)

    def update_setting(self, key: str, value) -> None:
        """Update a plugin setting value and persist to disk."""
        if self._plugin_settings is None:
            return
        setattr(self._plugin_settings, key, value)
        self.save_plugin_state()

    # ------------------------------------------------------------------
    # Lifecycle hook — override to rebuild state after settings load
    # ------------------------------------------------------------------

    def on_settings_loaded(self) -> None:  # noqa: B027
        """Called after settings are loaded from disk.

        Override to rebuild internal state (e.g. re-create a parser instance)
        from the restored settings values.
        """
        pass

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_plugin_state(self) -> None:
        data = {
            "settings": (
                self._plugin_settings.model_dump(mode="json")
                if self._plugin_settings
                else {}
            ),
        }
        config_file = Path.joinpath(self.get_plugin_data_path(), "data.json")
        try:
            with open(config_file, "w", encoding="UTF8") as f:
                json.dump(data, f)
        except (PermissionError, OSError) as e:
            _logger.error(f"Failed to save plugin state for {self.name}: {e}")

    def load_settings(self) -> None:
        config_file = Path.joinpath(self.get_plugin_data_path(), "data.json")
        try:
            with open(config_file, "r", encoding="UTF8") as f:
                data = json.load(f)
            if self._plugin_settings is not None:
                settings_data = data.get("settings", {})
                self._plugin_settings = self.plugin_settings_model.model_validate(
                    settings_data
                )
            self.on_settings_loaded()
        except FileNotFoundError:
            pass
        except (PermissionError, OSError) as e:
            _logger.error(f"Permission error loading settings for {self.name}: {e}")

    # ------------------------------------------------------------------
    # Plugin data directory helpers
    # ------------------------------------------------------------------

    def get_plugin_data_path(self) -> Path:
        """Returns the full path to a plugin's data directory."""
        plugin_data_path = Path.joinpath(
            utils.plugin_data_root(), clean_plugin_name(self.name)
        )
        if not plugin_data_path.is_dir():
            utils.create_directory(plugin_data_path)
        return plugin_data_path

    def get_plugin_data(self) -> list[Path]:
        """Returns all available files/folders in the plugin data directory."""
        return list(self.get_plugin_data_path().iterdir())

    # ------------------------------------------------------------------
    # Exception helpers
    # ------------------------------------------------------------------

    def file_not_valid_exception(self, exception_message: str):
        return FileNotValidError(value=exception_message)

    def directory_not_valid_exception(self, exception_message: str):
        return DirectoryNotValidError(value=exception_message)

    def file_type_invalid(self, exception_message: str):
        return FileTypeInvalidError(value=exception_message)


def clean_plugin_name(name: str) -> str:
    """Cleans the plugin name from any potentially problematic characters for Windows."""
    disallowed = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
    for char in disallowed:
        name = name.replace(char, "")
    return name
