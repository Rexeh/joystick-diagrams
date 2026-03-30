"""OpenKneeboard output plugin.

Copies exported PNG diagrams to the OpenKneeboard content directories so they
appear automatically in-cockpit without manual file management.

Two delivery modes are supported:

- DCS_KNEEBOARD: copies PNGs into the standard DCS kneeboard folder structure
      {Saved Games}/DCS.openbeta/KNEEBOARD/{aircraft}/
  Profile names are resolved to DCS module folder names via a built-in mapping
  plus an optional user-editable override file (aircraft_map.json in the
  plugin data directory).

- FOLDER_TAB: copies PNGs into a plain folder that can be added as a
  "Folder" tab inside OpenKneeboard settings.
"""

import json
import logging
import re
import shutil
from pathlib import Path

from pydantic import Field

from joystick_diagrams.plugins.output_plugin_interface import (
    ExportResult,
    OutputPluginInterface,
)
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings

from .aircraft_map import KNOWN_DCS_AIRCRAFT

_logger = logging.getLogger(__name__)

DCS_KNEEBOARD = "DCS_KNEEBOARD"
FOLDER_TAB = "FOLDER_TAB"


class OpenKneeboardSettings(PluginSettings):
    saved_games_path: Path | None = Field(
        default=None,
        title="DCS Saved Games Folder",
        json_schema_extra={
            "is_folder": True,
            "default_path": "~/Saved Games",
            "required": False,
        },
    )
    output_folder: Path | None = Field(
        default=None,
        title="Output Folder (Folder Tab mode)",
        json_schema_extra={
            "is_folder": True,
            "default_path": "~/Documents",
            "required": False,
        },
    )
    organize_by_profile: bool = Field(
        default=True,
        title="Organise by Profile",
        description="Create one subfolder per aircraft/profile name",
    )
    use_subfolder: bool = Field(
        default=True,
        title="Use JoystickDiagrams subfolder",
        description=(
            "Place files in a 'JoystickDiagrams' subfolder to avoid overwriting "
            "your existing kneeboard pages. OpenKneeboard shows each subfolder as "
            "its own tab. Disable to write directly into the aircraft kneeboard folder."
        ),
    )
    mode: str = Field(
        default=DCS_KNEEBOARD,
        title="Delivery Mode",
        json_schema_extra={"options": [DCS_KNEEBOARD, FOLDER_TAB]},
    )


class OutputPlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(
        name="OpenKneeboard",
        version="1.0.0",
        icon_path="img/openkneeboard.ico",
    )
    plugin_settings_model = OpenKneeboardSettings

    @property
    def ready(self) -> bool:
        mode = self.get_setting("mode")
        if mode == DCS_KNEEBOARD:
            return self.get_setting("saved_games_path") is not None
        return self.get_setting("output_folder") is not None

    def process_export(self, results: list[ExportResult]) -> bool:
        mode = self.get_setting("mode")
        organize = self.get_setting("organize_by_profile")
        use_subfolder = self.get_setting("use_subfolder")

        if mode == DCS_KNEEBOARD:
            return self._export_dcs_kneeboard(results, organize, use_subfolder)
        elif mode == FOLDER_TAB:
            return self._export_folder_tab(results, organize, use_subfolder)

        _logger.error(f"OpenKneeboard: unknown mode '{mode}'")
        return False

    # ------------------------------------------------------------------
    # Delivery implementations
    # ------------------------------------------------------------------

    def _export_dcs_kneeboard(
        self, results: list[ExportResult], organize: bool, use_subfolder: bool
    ) -> bool:
        saved_games = self.get_setting("saved_games_path")
        if saved_games is None:
            _logger.error("OpenKneeboard: saved_games_path is not configured")
            return False

        kneeboard_root = Path(saved_games) / "DCS.openbeta" / "KNEEBOARD"
        success = True

        for result in results:
            if not result.png_path.exists():
                _logger.warning(
                    f"OpenKneeboard: PNG not found, skipping: {result.png_path}"
                )
                continue

            if organize:
                aircraft_name = self._resolve_aircraft_name(result.profile_name)
                dest_dir = kneeboard_root / aircraft_name
            else:
                dest_dir = kneeboard_root

            if use_subfolder:
                dest_dir = dest_dir / "JoystickDiagrams"

            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / result.png_path.name
                shutil.copy2(result.png_path, dest_path)
                _logger.info(
                    f"OpenKneeboard: copied {result.png_path.name} → {dest_path}"
                )
            except (PermissionError, OSError) as e:
                _logger.error(f"OpenKneeboard: failed to copy {result.png_path}: {e}")
                success = False

        return success

    def _export_folder_tab(
        self, results: list[ExportResult], organize: bool, use_subfolder: bool
    ) -> bool:
        output_folder = self.get_setting("output_folder")
        if output_folder is None:
            _logger.error("OpenKneeboard: output_folder is not configured")
            return False

        success = True

        for result in results:
            if not result.png_path.exists():
                _logger.warning(
                    f"OpenKneeboard: PNG not found, skipping: {result.png_path}"
                )
                continue

            if organize:
                dest_dir = Path(output_folder) / _safe_folder_name(result.profile_name)
            else:
                dest_dir = Path(output_folder)

            if use_subfolder:
                dest_dir = dest_dir / "JoystickDiagrams"

            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / result.png_path.name
                shutil.copy2(result.png_path, dest_path)
                _logger.info(
                    f"OpenKneeboard: copied {result.png_path.name} → {dest_path}"
                )
            except (PermissionError, OSError) as e:
                _logger.error(f"OpenKneeboard: failed to copy {result.png_path}: {e}")
                success = False

        return success

    # ------------------------------------------------------------------
    # Aircraft name resolution
    # ------------------------------------------------------------------

    def _resolve_aircraft_name(self, profile_name: str) -> str:
        """Resolve a profile name to a DCS module folder name."""
        key = profile_name.strip().lower()

        # 1. User overrides (highest priority)
        user_map = self._load_user_aircraft_map()
        if key in user_map:
            return user_map[key]

        # 2. Built-in mapping
        if key in KNOWN_DCS_AIRCRAFT:
            return KNOWN_DCS_AIRCRAFT[key]

        # 3. Fallback: filesystem-safe version of the raw profile name
        return _safe_folder_name(profile_name)

    def _load_user_aircraft_map(self) -> dict[str, str]:
        """Load the user-editable aircraft_map.json from the plugin data directory."""
        map_file = self.get_plugin_data_path() / "aircraft_map.json"

        if not map_file.exists():
            try:
                map_file.write_text("{}", encoding="utf-8")
            except (PermissionError, OSError):
                pass
            return {}

        try:
            with open(map_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                k.lower(): v
                for k, v in data.items()
                if isinstance(k, str) and isinstance(v, str)
            }
        except (ValueError, OSError) as e:
            _logger.warning(f"OpenKneeboard: could not load aircraft_map.json: {e}")
            return {}


def _safe_folder_name(name: str) -> str:
    """Convert a profile name to a filesystem-safe folder name."""
    return re.sub(r'[<>:"/\\|?*]', "", name).strip().replace(" ", "_") or "Unknown"
