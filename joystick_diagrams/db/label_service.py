import logging

from joystick_diagrams.db import db_bind_text

_logger = logging.getLogger(__name__)


class LabelService:
    def __init__(self):
        self._cache: dict[str, str] = {}
        self._load_cache()

    def _load_cache(self):
        rows = db_bind_text.get_all_bind_text()
        self._cache = {original: replaced for original, replaced in rows}
        _logger.info(f"Loaded {len(self._cache)} custom labels from database")

    def resolve(self, command: str) -> str:
        return self._cache.get(command, command)

    def has_custom_label(self, command: str) -> bool:
        return command in self._cache

    def set_label(self, original: str, replaced: str) -> None:
        db_bind_text.add_update_bind_text(original, replaced)
        self._cache[original] = replaced

    def remove_label(self, original: str) -> None:
        db_bind_text.delete_bind_text(original)
        self._cache.pop(original, None)

    def remove_all_labels(self) -> None:
        for original in list(self._cache.keys()):
            db_bind_text.delete_bind_text(original)
        self._cache.clear()

    def get_all_custom_labels(self) -> dict[str, str]:
        return dict(self._cache)
