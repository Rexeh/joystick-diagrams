import logging

from joystick_diagrams.db import db_device_management

_logger = logging.getLogger(__name__)


class DeviceService:
    def __init__(self):
        self._hidden_cache: dict[str, str] = {}  # guid -> name
        self._custom_name_cache: dict[str, str] = {}  # guid -> custom_name
        self._load_cache()

    def _load_cache(self):
        rows = db_device_management.get_hidden_devices()
        self._hidden_cache = {guid: (name or guid) for guid, name in rows}
        _logger.info(f"Loaded {len(self._hidden_cache)} hidden devices from database")

        self._custom_name_cache = db_device_management.get_all_device_custom_names()
        _logger.info(
            f"Loaded {len(self._custom_name_cache)} custom device names from database"
        )

    def is_hidden(self, guid: str) -> bool:
        return guid in self._hidden_cache

    def set_hidden(self, guid: str, name: str, hidden: bool) -> None:
        db_device_management.set_device_hidden(guid, name, hidden)
        if hidden:
            self._hidden_cache[guid] = name
        else:
            self._hidden_cache.pop(guid, None)

    def get_all_hidden(self) -> dict[str, str]:
        """Returns dict of guid -> name for all hidden devices."""
        return dict(self._hidden_cache)

    # ── Custom device names ──

    def resolve_name(self, guid: str, original_name: str) -> str:
        """Return custom name if set, otherwise the original name."""
        return self._custom_name_cache.get(guid, original_name)

    def get_custom_name(self, guid: str) -> str | None:
        return self._custom_name_cache.get(guid)

    def set_custom_name(self, guid: str, custom_name: str | None) -> None:
        db_device_management.set_device_custom_name(guid, custom_name)
        if custom_name:
            self._custom_name_cache[guid] = custom_name
        else:
            self._custom_name_cache.pop(guid, None)
