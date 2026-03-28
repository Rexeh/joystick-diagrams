import logging

from joystick_diagrams.db import db_device_management

_logger = logging.getLogger(__name__)


class DeviceService:
    def __init__(self):
        self._hidden_cache: dict[str, str] = {}  # guid -> name
        self._load_cache()

    def _load_cache(self):
        rows = db_device_management.get_hidden_devices()
        self._hidden_cache = {guid: (name or guid) for guid, name in rows}
        _logger.info(f"Loaded {len(self._hidden_cache)} hidden devices from database")

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
