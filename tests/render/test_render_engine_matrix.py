"""Engine selection matrix for the style/modifier opt-ins and the context snapshot."""

from unittest.mock import patch

import pytest

from joystick_diagrams.input.button import Button
from joystick_diagrams.modifier_identity import (
    MODIFIER_COLOURING_SETTING_KEY,
    MODIFIER_DISPLAY_SETTING_KEY,
    MODIFIER_KEY_DISPLAY_SETTING_KEY,
    ModifierDisplay,
    ModifierKeyDisplay,
    ModifierRegistrySnapshot,
)
from joystick_diagrams.render import (
    ACTIVE_THEME_SETTING_KEY,
    Engine,
    RenderContext,
    build_render_context,
    choose_engine,
)
from joystick_diagrams.render.theme import CLEAN_THEME
from tests.render.render_fixtures import export_device_for, new_device


def ed():
    dev = new_device()
    dev.create_input(Button(1), "Fire")
    return export_device_for("BUTTON_1", dev)


def registry(**kw):
    return ModifierRegistrySnapshot.default(**kw)


@pytest.mark.parametrize(
    ("ctx", "expected"),
    [
        (RenderContext(), Engine.LEGACY),
        (
            RenderContext(modifier_display=ModifierDisplay.MERGED_SAME_LINE),
            Engine.LEGACY,
        ),
        (RenderContext(registry=registry()), Engine.LEGACY),
        (RenderContext(theme=CLEAN_THEME), Engine.DOM),
        (RenderContext(colour_modifiers=True), Engine.DOM),
        (RenderContext(modifier_display=ModifierDisplay.UNDER_MAIN_TEXT), Engine.DOM),
        (
            RenderContext(registry=registry(key_display=ModifierKeyDisplay.SIMPLIFIED)),
            Engine.DOM,
        ),
        (RenderContext(engine_override="dom"), Engine.DOM),
        (
            RenderContext(
                theme=CLEAN_THEME,
                colour_modifiers=True,
                modifier_display=ModifierDisplay.UNDER_MAIN_TEXT,
                engine_override="legacy",
            ),
            Engine.LEGACY,
        ),
    ],
    ids=[
        "default",
        "merged-same-line",
        "registry-off",
        "theme",
        "colouring",
        "under-main-text",
        "simplified-keys",
        "dom-override",
        "legacy-override-wins",
    ],
)
def test_choose_engine_matrix(ctx, expected):
    assert choose_engine(ctx, ed()) is expected


def _settings(values):
    return patch("joystick_diagrams.db.db_settings.get_setting", side_effect=values.get)


def test_build_render_context_defaults_to_original_without_app_state():
    ctx = build_render_context()
    assert ctx.theme is None
    assert ctx.colour_modifiers is False
    assert ctx.registry is not None and ctx.registry.colouring_enabled is False
    assert ctx.modifier_display is ModifierDisplay.TEMPLATE_BOXES
    assert choose_engine(ctx, ed()) is Engine.LEGACY


def test_build_render_context_snapshots_the_opt_ins():
    with _settings(
        {
            ACTIVE_THEME_SETTING_KEY: "clean",
            MODIFIER_COLOURING_SETTING_KEY: "true",
            MODIFIER_DISPLAY_SETTING_KEY: "UNDER_MAIN_TEXT",
            MODIFIER_KEY_DISPLAY_SETTING_KEY: "SIMPLIFIED",
        }
    ):
        ctx = build_render_context()
    assert ctx.theme is not None and ctx.theme.theme_id == "clean"
    assert ctx.colour_modifiers is True and ctx.registry.colouring_enabled is True
    assert ctx.modifier_display is ModifierDisplay.UNDER_MAIN_TEXT
    assert ctx.simplified_key_names is True
    assert choose_engine(ctx, ed()) is Engine.DOM


def test_unknown_active_theme_means_original():
    with _settings({ACTIVE_THEME_SETTING_KEY: "user_missing"}):
        assert build_render_context().theme is None
