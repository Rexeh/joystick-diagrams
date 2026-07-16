import logging

from joystick_diagrams.db import db_device_aliases

_logger = logging.getLogger(__name__)


class DeviceAliasService:
    def __init__(self):
        self._cache: dict[str, str] = {}  # source_guid -> target_guid
        self._load_cache()

    def _load_cache(self):
        rows = db_device_aliases.get_all_aliases()
        self._cache = {source: target for source, target in rows}
        _logger.info(f"Loaded {len(self._cache)} device aliases from database")

    def resolve(self, guid: str) -> str:
        return self._cache.get(guid, guid)

    def set_alias(self, source_guid: str, target_guid: str) -> None:
        if source_guid == target_guid:
            raise ValueError("cannot alias a device to itself")

        if target_guid in self._cache:
            raise ValueError(
                f"target is already aliased to {self._cache[target_guid]} — chained aliases are not supported"
            )

        # Build the set of all current targets, excluding the current source's
        # existing target (so overwriting an alias is allowed, and fan-in is allowed).
        existing_target = self._cache.get(source_guid)
        target_set = {v for k, v in self._cache.items() if k != source_guid}
        if existing_target is not None:
            # Don't exclude the target if other sources also point to it (fan-in)
            other_sources_to_same = any(
                v == existing_target for k, v in self._cache.items() if k != source_guid
            )
            if not other_sources_to_same:
                target_set.discard(existing_target)

        if source_guid in target_set:
            raise ValueError(
                "source is already a target of another alias — chained aliases are not supported"
            )

        db_device_aliases.add_update_alias(source_guid, target_guid)
        self._cache[source_guid] = target_guid

    def remove_alias(self, source_guid: str) -> None:
        db_device_aliases.delete_alias(source_guid)
        self._cache.pop(source_guid, None)

    def get_all_aliases(self) -> dict[str, str]:
        return dict(self._cache)
