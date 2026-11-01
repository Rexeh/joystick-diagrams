"""Theme model: merge/resolution semantics, built-ins and the active-style setting."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from joystick_diagrams.render.theme import (
    ACTIVE_THEME_SETTING_KEY,
    BUILTIN_THEMES,
    CLEAN_THEME,
    ORIGINAL_THEME_NAME,
    TEMPLATE_ORIGINAL_THEME_ID,
    BoxStyle,
    LineStyle,
    RoleStyle,
    TextStyle,
    Theme,
    ThemeRole,
    builtin_theme,
    font_stack,
    get_active_theme_id,
    is_builtin_theme_id,
    is_original_theme_id,
    merge_themes,
    resolve_theme,
    set_active_theme_id,
    theme_display_name,
)


def _theme(theme_id="t", **roles) -> Theme:
    return Theme(theme_id=theme_id, name=theme_id, roles=roles)


# ── Model ──


def test_colour_is_validated():
    TextStyle(colour="#AABBCC")
    TextStyle(colour="#aabbccdd")
    with pytest.raises(ValidationError):
        TextStyle(colour="red")
    with pytest.raises(ValidationError):
        BoxStyle(stroke="#ABC")


def test_missing_role_is_empty_and_unknown_json_keys_are_ignored():
    theme = Theme.model_validate(
        {
            "theme_id": "x",
            "name": "x",
            "roles": {"BOUND": {"text": {"colour": "#000000", "future": 1}}},
        }
    )
    assert theme.text(ThemeRole.BOUND).colour == "#000000"
    assert theme.role(ThemeRole.DATE) == RoleStyle()
    assert theme.box(ThemeRole.TITLE).is_empty()


def test_json_round_trip_keeps_schema_version():
    restored = Theme.model_validate_json(CLEAN_THEME.model_dump_json())
    assert restored == CLEAN_THEME
    assert restored.schema_version == 1


# ── Merge / resolve ──


def test_merge_takes_first_non_none_from_the_top():
    base = _theme(
        "base",
        BOUND=RoleStyle(
            text=TextStyle(colour="#111111", font_size=9),
            box=BoxStyle(stroke="#222222"),
        ),
    )
    over = _theme(
        "over", BOUND=RoleStyle(text=TextStyle(colour="#333333"), box=BoxStyle())
    )
    merged = merge_themes(base, over)
    assert merged is not None
    assert merged.theme_id == "over"
    assert merged.text(ThemeRole.BOUND).colour == "#333333"  # top wins
    assert merged.text(ThemeRole.BOUND).font_size == 9  # None inherits
    assert merged.box(ThemeRole.BOUND).stroke == "#222222"


def test_merge_unions_roles_and_leader_line():
    base = Theme(
        theme_id="b", name="b", leader_line=LineStyle(stroke="#000000", stroke_width=1)
    )
    over = _theme("o", TITLE=RoleStyle(text=TextStyle(font_weight="bold")))
    over = over.model_copy(update={"leader_line": LineStyle(stroke_width=3)})
    merged = merge_themes(base, over)
    assert merged.text(ThemeRole.TITLE).font_weight == "bold"
    assert merged.leader_line == LineStyle(stroke="#000000", stroke_width=3)


def test_merge_skips_none_layers_and_returns_none_for_nothing():
    assert merge_themes(None, None) is None
    assert merge_themes(None, CLEAN_THEME, None) == CLEAN_THEME


def test_resolve_original_is_none_and_author_sits_below_user():
    assert resolve_theme(None) is None
    author = _theme("author", DATE=RoleStyle(text=TextStyle(colour="#ABCDEF")))
    user = _theme("user", DATE=RoleStyle(text=TextStyle(font_size=7)))
    resolved = resolve_theme(user, author=author)
    assert resolved.theme_id == "user"
    assert resolved.text(ThemeRole.DATE).colour == "#ABCDEF"
    assert resolved.text(ThemeRole.DATE).font_size == 7
    assert resolve_theme(user) == user


# ── Built-ins and names ──


def test_builtins_are_three_distinct_valid_themes():
    assert list(BUILTIN_THEMES) == ["clean", "print_friendly", "high_contrast"]
    names = {t.name for t in BUILTIN_THEMES.values()}
    assert names == {"Clean", "Print friendly", "High contrast"}
    for theme in BUILTIN_THEMES.values():
        assert theme.based_on is None
        assert ThemeRole.BOUND in theme.roles and ThemeRole.UNBOUND in theme.roles


def test_identity_helpers():
    assert is_original_theme_id(None) and is_original_theme_id(
        TEMPLATE_ORIGINAL_THEME_ID
    )
    assert is_builtin_theme_id("clean") and not is_builtin_theme_id("user_1")
    assert builtin_theme("print_friendly").name == "Print friendly"
    assert builtin_theme(TEMPLATE_ORIGINAL_THEME_ID) is None
    assert theme_display_name(None) == ORIGINAL_THEME_NAME
    assert theme_display_name("nope") == ORIGINAL_THEME_NAME
    assert theme_display_name("clean") == "Clean"
    assert theme_display_name("u1", [_theme("u1")]) == "u1"


def test_font_stack_quotes_unknown_multiword_families():
    assert font_stack("Arial").startswith("Arial")
    assert font_stack("noto sans") == '"Noto Sans", Arial, sans-serif'
    assert font_stack("My Font") == '"My Font", sans-serif'
    assert font_stack("Mono") == "Mono, sans-serif"


# ── Setting ──


def test_active_theme_id_reads_at_call_time():
    assert get_active_theme_id() == TEMPLATE_ORIGINAL_THEME_ID  # conftest: None
    with patch(
        "joystick_diagrams.db.db_settings.get_setting",
        side_effect={ACTIVE_THEME_SETTING_KEY: " clean "}.get,
    ):
        assert get_active_theme_id() == "clean"
    with patch("joystick_diagrams.db.db_settings.add_update_setting_value") as write:
        set_active_theme_id(None)
        write.assert_called_once_with(
            ACTIVE_THEME_SETTING_KEY, TEMPLATE_ORIGINAL_THEME_ID
        )
