"""Settings for the four-stage workflow shell (call-time lookups, like
``conflict_strategy`` and ``modifier_identity``).

- ``auto_read_on_launch``: read the games again in the background on every
  launch (default on; Settings can turn it off).
- ``export_folder``: where diagrams are saved. No default: ``None`` until the
  user chooses one at the first export; a remembered folder that no longer
  exists is reported as ``None`` again so the app asks once more. Stored under
  the key the old Export screen used so a chosen folder carries over.
- ``export_ticks``: which rows of the Export list are ticked, remembered between
  sessions as JSON ``{"<row key>": true|false}``; rows without an entry use the
  caller's default (every ready profile ticked).
- ``last_stage``: the stage index (0–3) the user was on, for the returning launch.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from joystick_diagrams.db import db_settings

_logger = logging.getLogger(__name__)

AUTO_READ_ON_LAUNCH_SETTING_KEY = "auto_read_on_launch"
EXPORT_FOLDER_SETTING_KEY = "export_path"  # shared with ui/export_settings.py
EXPORT_TICKS_SETTING_KEY = "export_ticks"
LAST_STAGE_SETTING_KEY = "last_stage"

DEFAULT_AUTO_READ_ON_LAUNCH = True
STAGE_COUNT = 4
FIRST_STAGE = 0
LAST_STAGE_INDEX = STAGE_COUNT - 1

_TRUE = {"true", "1", "yes", "on"}
_FALSE = {"false", "0", "no", "off"}


def _bool_setting(key: str, default: bool) -> bool:
    raw = db_settings.get_setting(key)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    _logger.warning(f"Invalid boolean in settings for {key}: {raw!r}, using default")
    return default


# ── Auto-read on launch ──


def get_auto_read_on_launch() -> bool:
    return _bool_setting(AUTO_READ_ON_LAUNCH_SETTING_KEY, DEFAULT_AUTO_READ_ON_LAUNCH)


def set_auto_read_on_launch(enabled: bool) -> None:
    db_settings.add_update_setting_value(
        AUTO_READ_ON_LAUNCH_SETTING_KEY, "true" if enabled else "false"
    )


# The "what the automatic read keeps" popover opens by itself only the first
# time a read runs at launch; afterwards it is on demand (click the 1. Setup
# tab's status) so a returning user is not interrupted on every start.
READ_POPOVER_SHOWN_SETTING_KEY = "read_popover_shown"


def get_read_popover_shown() -> bool:
    return _bool_setting(READ_POPOVER_SHOWN_SETTING_KEY, False)


def set_read_popover_shown(shown: bool) -> None:
    db_settings.add_update_setting_value(
        READ_POPOVER_SHOWN_SETTING_KEY, "true" if shown else "false"
    )


# ── Export folder ──


def get_export_folder() -> Path | None:
    """The chosen export folder, or ``None`` when none is chosen or it is gone."""
    raw = db_settings.get_setting(EXPORT_FOLDER_SETTING_KEY)
    if not raw or not raw.strip():
        return None
    path = Path(raw.strip())
    if not path.is_dir():
        _logger.info(f"Export folder {path} is not available; asking again")
        return None
    return path


def get_export_folder_raw() -> str | None:
    """The stored value even when the folder is missing (to say which one is gone)."""
    raw = db_settings.get_setting(EXPORT_FOLDER_SETTING_KEY)
    return raw.strip() if raw and raw.strip() else None


def set_export_folder(folder: Path | str | None) -> None:
    db_settings.add_update_setting_value(
        EXPORT_FOLDER_SETTING_KEY, str(folder) if folder else ""
    )


# ── Remembered export ticks ──


def get_export_ticks() -> dict[str, bool]:
    raw = db_settings.get_setting(EXPORT_TICKS_SETTING_KEY)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        _logger.warning("Invalid export ticks in settings, ignoring")
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): bool(value) for key, value in data.items()}


def set_export_ticks(ticks: dict[str, bool]) -> None:
    db_settings.add_update_setting_value(
        EXPORT_TICKS_SETTING_KEY,
        json.dumps({str(k): bool(v) for k, v in ticks.items()}, sort_keys=True),
    )


def is_export_ticked(row_key: str, default: bool = True) -> bool:
    return get_export_ticks().get(row_key, default)


def set_export_tick(row_key: str, ticked: bool) -> None:
    ticks = get_export_ticks()
    ticks[row_key] = ticked
    set_export_ticks(ticks)


# ── Last stage ──


def get_last_stage() -> int | None:
    """The stage index the user was on, or ``None`` when never recorded."""
    raw = db_settings.get_setting(LAST_STAGE_SETTING_KEY)
    if raw is None or not raw.strip():
        return None
    try:
        stage = int(raw)
    except ValueError:
        _logger.warning(f"Invalid last stage in settings: {raw!r}")
        return None
    return min(max(stage, FIRST_STAGE), LAST_STAGE_INDEX)


def set_last_stage(stage: int) -> None:
    db_settings.add_update_setting_value(
        LAST_STAGE_SETTING_KEY, str(min(max(int(stage), FIRST_STAGE), LAST_STAGE_INDEX))
    )


if __name__ == "__main__":
    pass
