"""Theme persistence and ThemeService (in-memory sqlite, dict-backed settings)."""

import sqlite3
from unittest.mock import patch

import pytest

from joystick_diagrams.db import db_themes
from joystick_diagrams.db.theme_service import ThemeService, copy_name
from joystick_diagrams.render.theme import (
    ACTIVE_THEME_SETTING_KEY,
    TEMPLATE_ORIGINAL_THEME_ID,
    Theme,
    ThemeRole,
)


@pytest.fixture(autouse=True)
def mock_connection():
    conn = sqlite3.connect(":memory:")
    with patch("joystick_diagrams.db.db_themes.connection", return_value=conn):
        db_themes.create_new_db_if_not_exist()
        yield conn
    conn.close()


@pytest.fixture(autouse=True)
def settings():
    values: dict[str, str] = {}
    with (
        patch("joystick_diagrams.db.db_settings.get_setting", side_effect=values.get),
        patch(
            "joystick_diagrams.db.db_settings.add_update_setting_value",
            side_effect=values.__setitem__,
        ),
    ):
        yield values


def _user(theme_id="user_a", name="Mine") -> Theme:
    return Theme(theme_id=theme_id, name=name, based_on="clean")


class TestDBThemes:
    def test_upsert_get_delete(self):
        db_themes.upsert_theme("user_a", "Mine", "{}")
        db_themes.upsert_theme("user_a", "Mine 2", '{"a": 1}')
        rows = db_themes.get_all_themes()
        assert [(r[0], r[1], r[2]) for r in rows] == [("user_a", "Mine 2", '{"a": 1}')]
        assert rows[0][3]  # updated_at
        db_themes.delete_theme("user_a")
        assert db_themes.get_all_themes() == []


class TestThemeService:
    def test_builtins_first_then_user_by_name(self):
        service = ThemeService()
        service.save(_user("user_b", "Zed"))
        service.save(_user("user_a", "alpha"))
        names = [t.name for t in service.all_themes()]
        assert names == ["Clean", "Print friendly", "High contrast", "alpha", "Zed"]
        assert service.get("clean").name == "Clean"
        assert service.get(TEMPLATE_ORIGINAL_THEME_ID) is None
        assert service.get("nope") is None

    def test_invalid_rows_are_skipped_on_load(self):
        db_themes.upsert_theme("bad", "Bad", '{"name": 3}')
        db_themes.upsert_theme(
            "user_ok", "Ok", _user("user_ok", "Ok").model_dump_json()
        )
        service = ThemeService()
        assert [t.theme_id for t in service.user_themes()] == ["user_ok"]

    def test_save_rejects_builtins_blank_and_duplicate_names(self):
        service = ThemeService()
        with pytest.raises(ValueError):
            service.save(Theme(theme_id="clean", name="Clean"))
        with pytest.raises(ValueError):
            service.save(_user(name="  "))
        with pytest.raises(ValueError):
            service.save(_user("user_x", "print FRIENDLY"))
        service.save(_user("user_a", "Mine"))
        with pytest.raises(ValueError):
            service.save(_user("user_b", "mine"))
        service.save(_user("user_a", "Mine"))  # same id, same name: fine

    def test_write_through_survives_reload(self):
        service = ThemeService()
        theme = _user()
        theme.roles[ThemeRole.BOUND] = theme.role(ThemeRole.BOUND)
        theme.roles[ThemeRole.BOUND].text.colour = "#123456"
        service.save(theme)
        reloaded = ThemeService()
        assert reloaded.get("user_a").text(ThemeRole.BOUND).colour == "#123456"

    def test_ensure_editable_copies_builtin_names_it_and_activates(self, settings):
        service = ThemeService()
        copy = service.ensure_editable("print_friendly")
        assert copy.theme_id.startswith("user_")
        assert copy.name == "My style (based on Print friendly)"
        assert copy.based_on == "print_friendly"
        assert copy.roles == service.get("print_friendly").roles
        assert settings[ACTIVE_THEME_SETTING_KEY] == copy.theme_id
        assert service.ensure_editable(copy.theme_id) is copy  # already editable

        second = service.ensure_editable("print_friendly")
        assert second.name == "My style (based on Print friendly) 2"
        with pytest.raises(ValueError):
            service.ensure_editable(TEMPLATE_ORIGINAL_THEME_ID)

    def test_copy_name_suffixes(self):
        assert copy_name("Clean", set()) == "My style (based on Clean)"
        taken = {"My style (based on Clean)", "My style (based on Clean) 2"}
        assert copy_name("Clean", taken) == "My style (based on Clean) 3"

    def test_active_falls_back_to_original_and_delete_resets_it(self, settings):
        service = ThemeService()
        assert service.active_theme_id() == TEMPLATE_ORIGINAL_THEME_ID
        assert service.resolved_active() is None
        settings[ACTIVE_THEME_SETTING_KEY] = "ghost"
        assert service.active_theme_id() == TEMPLATE_ORIGINAL_THEME_ID

        assert service.set_active("clean") == "clean"
        assert service.resolved_active().theme_id == "clean"
        saved = service.save(_user())
        service.set_active(saved.theme_id)
        service.delete(saved.theme_id)
        assert settings[ACTIVE_THEME_SETTING_KEY] == TEMPLATE_ORIGINAL_THEME_ID
        assert service.get(saved.theme_id) is None
        with pytest.raises(ValueError):
            service.delete("clean")

    def test_reset_to_base_restores_builtin_values(self):
        service = ThemeService()
        copy = service.ensure_editable("clean")
        edited = copy.model_copy(deep=True)
        edited.roles[ThemeRole.BOUND].text.colour = "#FF0000"
        service.save(edited)
        restored = service.reset_to_base(copy.theme_id)
        assert restored.name == copy.name
        assert (
            restored.text(ThemeRole.BOUND).colour
            == service.get("clean").text(ThemeRole.BOUND).colour
        )
        with pytest.raises(ValueError):
            service.reset_to_base("clean")
