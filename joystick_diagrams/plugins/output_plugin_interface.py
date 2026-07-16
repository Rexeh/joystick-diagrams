import inspect
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from joystick_diagrams import utils
from joystick_diagrams.input.device import Device_
from joystick_diagrams.plugins.plugin_interface import clean_plugin_name
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExportResult:
    """Metadata and data for a single exported file, passed to output plugins.

    Provides both export context (paths, format) and the full device input model
    so output plugins can work with binding data directly without needing images.
    """

    profile_name: str
    device_name: str
    device_guid: str
    source_plugin: str
    template_name: str | None
    export_format: str  # "SVG" or "PNG"
    file_path: Path  # the primary output file (SVG or PNG)
    export_directory: Path
    device: Device_  # full device model with all inputs, axes, hats, modifiers


class OutputPluginInterface(ABC):
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

    @abstractmethod
    def process_export(self, results: list[ExportResult]) -> bool:
        """Called after export completes (SVG or PNG). Return True on success."""
        ...

    @property
    def name(self) -> str:
        return self.plugin_meta.name

    @property
    def version(self) -> str:
        return self.plugin_meta.version

    @property
    def icon(self) -> str:
        plugin_dir = Path(inspect.getfile(type(self))).parent
        return str(plugin_dir / self.plugin_meta.icon_path)

    @property
    def ready(self) -> bool:
        if self._plugin_settings is None:
            return True
        for field_name, field_info in type(self._plugin_settings).model_fields.items():
            annotation = field_info.annotation
            is_path = annotation is Path or (
                hasattr(annotation, "__args__") and Path in annotation.__args__
            )
            if not is_path:
                continue
            extra = field_info.json_schema_extra or {}
            if extra.get("required", True):
                if getattr(self._plugin_settings, field_name) is None:
                    return False
        return True

    def get_setting(self, key: str):
        if self._plugin_settings is None:
            return None
        return getattr(self._plugin_settings, key, None)

    def update_setting(self, key: str, value) -> None:
        if self._plugin_settings is None:
            return
        setattr(self._plugin_settings, key, value)
        self.save_plugin_state()

    def on_settings_loaded(self) -> None:  # noqa: B027
        pass

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
            if (
                self._plugin_settings is not None
                and self.plugin_settings_model is not None
            ):
                settings_data = data.get("settings", {})
                self._plugin_settings = self.plugin_settings_model.model_validate(
                    settings_data
                )
            self.on_settings_loaded()
        except FileNotFoundError:
            pass
        except (ValueError, KeyError) as e:
            _logger.warning(
                f"Discarding unreadable settings for {self.name} (old format?): {e}"
            )
        except (PermissionError, OSError) as e:
            _logger.error(f"Permission error loading settings for {self.name}: {e}")

    def get_plugin_data_path(self) -> Path:
        plugin_data_path = Path.joinpath(
            utils.plugin_data_root(), clean_plugin_name(self.name)
        )
        if not plugin_data_path.is_dir():
            utils.create_directory(plugin_data_path)
        return plugin_data_path

    def get_plugin_data(self) -> list[Path]:
        return list(self.get_plugin_data_path().iterdir())
