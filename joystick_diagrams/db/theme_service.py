"""Cached, write-through access to styles: the read-only built-ins plus user copies.

Mirrors ``DeviceAliasService``/``ModifierKeyService``: a dict cache loaded once,
every write goes to the database and the cache together, invalid rows are
logged and skipped (as ``OutputPluginInterface.load_settings`` does), and
``ValueError`` is raised for duplicate names and for writing or deleting built-ins.

Editing a built-in never edits it: ``ensure_editable`` silently creates
"My style (based on <name>)", makes it the active style and returns the copy.
"""

import logging
import uuid

from pydantic import ValidationError

from joystick_diagrams.db import db_themes
from joystick_diagrams.render.theme import (
    BUILTIN_THEMES,
    TEMPLATE_ORIGINAL_THEME_ID,
    Theme,
    get_active_theme_id,
    is_builtin_theme_id,
    is_original_theme_id,
    resolve_theme,
    set_active_theme_id,
)

_logger = logging.getLogger(__name__)

USER_THEME_ID_PREFIX = "user_"


def copy_name(base_name: str, taken: set[str]) -> str:
    """ "My style (based on X)", with a numeric suffix when the name is taken."""
    candidate = f"My style (based on {base_name})"
    name = candidate
    suffix = 2
    while name in taken:
        name = f"{candidate} {suffix}"
        suffix += 1
    return name


class ThemeService:
    def __init__(self):
        self._user: dict[str, Theme] = {}
        self._load_cache()

    # ── Loading ────────────────────────────────────────────────────────

    def _load_cache(self) -> None:
        self._user = {}
        for theme_id, _name, theme_json, _updated in db_themes.get_all_themes():
            try:
                theme = Theme.model_validate_json(theme_json)
            except ValidationError as err:
                _logger.warning(f"Skipping invalid stored style {theme_id!r}: {err}")
                continue
            if theme.theme_id != theme_id:
                theme = theme.model_copy(update={"theme_id": theme_id})
            self._user[theme_id] = theme
        _logger.info(f"Loaded {len(self._user)} user styles from database")

    # ── Read API ───────────────────────────────────────────────────────

    def builtin_themes(self) -> list[Theme]:
        return list(BUILTIN_THEMES.values())

    def user_themes(self) -> list[Theme]:
        return sorted(self._user.values(), key=lambda t: t.name.casefold())

    def all_themes(self) -> list[Theme]:
        """Built-ins first, then user styles by name. Original is not a ``Theme``."""
        return self.builtin_themes() + self.user_themes()

    def get(self, theme_id: str | None) -> Theme | None:
        """A theme by id; ``None`` for Original and unknown ids."""
        if is_original_theme_id(theme_id):
            return None
        return BUILTIN_THEMES.get(theme_id) or self._user.get(theme_id or "")

    def is_builtin(self, theme_id: str | None) -> bool:
        return is_builtin_theme_id(theme_id)

    def active_theme_id(self) -> str:
        """The stored active id, or Original when it points at nothing."""
        theme_id = get_active_theme_id()
        if self.get(theme_id) is None:
            return TEMPLATE_ORIGINAL_THEME_ID
        return theme_id

    def active_theme(self) -> Theme | None:
        return self.get(self.active_theme_id())

    def resolved_active(self) -> Theme | None:
        """What ``RenderContext.theme`` should carry: ``None`` for Original."""
        return resolve_theme(self.active_theme())

    # ── Write API ──────────────────────────────────────────────────────

    def set_active(self, theme_id: str | None) -> str:
        """Make a style active (unknown ids fall back to Original). Returns the stored id."""
        chosen = (
            theme_id if self.get(theme_id) is not None else TEMPLATE_ORIGINAL_THEME_ID
        )
        set_active_theme_id(chosen)
        return chosen

    def save(self, theme: Theme) -> Theme:
        """Create or update a user style. Raises ``ValueError`` for built-ins and name clashes."""
        if is_original_theme_id(theme.theme_id) or self.is_builtin(theme.theme_id):
            raise ValueError("built-in styles cannot be changed; edit a copy instead")
        name = " ".join(theme.name.split())
        if not name:
            raise ValueError("a style needs a name")
        if any(
            other.name.casefold() == name.casefold()
            for other in self.all_themes()
            if other.theme_id != theme.theme_id
        ):
            raise ValueError(f"a style named {name!r} already exists")
        stored = theme.model_copy(update={"name": name})
        db_themes.upsert_theme(stored.theme_id, stored.name, stored.model_dump_json())
        self._user[stored.theme_id] = stored
        return stored

    def delete(self, theme_id: str) -> None:
        """Delete a user style; the active style falls back to Original if needed."""
        if self.is_builtin(theme_id) or is_original_theme_id(theme_id):
            raise ValueError("built-in styles cannot be deleted")
        db_themes.delete_theme(theme_id)
        self._user.pop(theme_id, None)
        if get_active_theme_id() == theme_id:
            set_active_theme_id(TEMPLATE_ORIGINAL_THEME_ID)

    def ensure_editable(self, theme_id: str) -> Theme:
        """The user style to edit for ``theme_id``: itself, or a fresh copy of a built-in.

        Copying a built-in names the copy "My style (based on <name>)" and makes
        it the active style, so the user never sees a Duplicate step.
        """
        existing = self._user.get(theme_id)
        if existing is not None:
            return existing
        base = BUILTIN_THEMES.get(theme_id)
        if base is None:
            raise ValueError(f"unknown style {theme_id!r}")
        copy = base.model_copy(
            update={
                "theme_id": f"{USER_THEME_ID_PREFIX}{uuid.uuid4().hex}",
                "name": copy_name(base.name, {t.name for t in self.all_themes()}),
                "based_on": base.theme_id,
            },
            deep=True,
        )
        stored = self.save(copy)
        self.set_active(stored.theme_id)
        return stored

    def reset_to_base(self, theme_id: str) -> Theme:
        """Restore a user style to the built-in it was based on (keeps id and name)."""
        theme = self._user.get(theme_id)
        if theme is None:
            raise ValueError(f"{theme_id!r} is not a user style")
        base = BUILTIN_THEMES.get(theme.based_on or "")
        if base is None:
            raise ValueError(f"{theme.name!r} has no built-in to reset to")
        restored = base.model_copy(
            update={
                "theme_id": theme.theme_id,
                "name": theme.name,
                "based_on": base.theme_id,
            },
            deep=True,
        )
        return self.save(restored)


if __name__ == "__main__":
    pass
