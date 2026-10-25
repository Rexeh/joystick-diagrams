"""Save-as-template bake: tokens kept, new placeholders discoverable, both engines."""

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from joystick_diagrams.export import render_template
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
from joystick_diagrams.render import RenderContext
from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.layout import (
    AddModifierBoxesOp,
    AddModifierBoxOp,
    AddNoteOp,
    HideOp,
    LayoutDocument,
    LayoutLayers,
    MoveOp,
)
from joystick_diagrams.render.template_writer import (
    JD_THEME_ATTRIBUTE,
    TemplateBakeError,
    bake_template,
    safe_template_filename,
    write_template,
)
from joystick_diagrams.render.theme import builtin_theme
from joystick_diagrams.template import Template

STARTER = Path(__file__).resolve().parents[2] / "templates" / "Starter Template.svg"


@dataclass
class Wrapper:
    profile_name: str


@dataclass
class ExportDeviceLike:
    template: object
    profile_wrapper: Wrapper
    device: Device_

    @property
    def template_file_name(self):
        return self.template.template_file_name


def device_with_modifiers() -> Device_:
    dev = Device_("666ec0a0-556b-11ee-8002-444553540000", "Stick")
    dev.create_input(Button(1), "Fire")
    dev.create_input(Button(2), "Gear")
    for key in ("LShift", "LCtrl", "LAlt"):
        dev.add_modifier_to_input(Button(2), {key}, f"Gear ({key})")
    return dev


def layers() -> LayoutLayers:
    return LayoutLayers(
        LayoutDocument(
            ops=[
                MoveOp(target="button_1", dx=20, dy=10),
                AddModifierBoxOp(
                    target="button_1", index=5, dx=0, dy=44, width=100, height=20
                ),
                HideOp(target="button_5"),
                AddNoteOp(
                    text="PROFILE_NAME · CURRENT_DATE",
                    x=20,
                    y=700,
                    width=220,
                    height=26,
                ),
                AddModifierBoxesOp(target="button_2", count="auto"),
            ]
        )
    )


@pytest.fixture
def baked(tmp_path):
    template = Template(str(STARTER))
    result = bake_template(template, layers(), device=device_with_modifiers())
    path = write_template(result.svg_text, tmp_path, "Starter – with modifier boxes")
    return template, result, path


def test_bake_keeps_tokens_and_adds_real_placeholders(baked):
    original, result, path = baked
    assert path.name == "Starter – with modifier boxes.svg"
    assert result.added_boxes == 5 and not result.skipped_ops
    text = result.svg_text
    assert "data-jd-" not in text
    assert "TEMPLATE_NAME" in text and "CURRENT_DATE" in text
    assert "Fire" not in text  # bindings were NOT filled
    # Old-app compatible discovery sees the new keys
    saved = Template(str(path))
    new_keys = saved.get_template_modifiers() - original.get_template_modifiers()
    assert new_keys == {
        "button_1_modifier_5",
        "button_2_modifier_1",
        "button_2_modifier_2",
        "button_2_modifier_3",
    }
    assert saved.get_template_buttons() == original.get_template_buttons()
    assert saved.template_name and saved.date
    # ... and the draw.io model carries them too
    doc = TemplateDocument.parse(text)
    model = DrawioModel.from_content(doc.root.get("content"))
    added = [c for c in model.cells() if "jdAdded=1" in (c.element.get("style") or "")]
    labels = sorted(c.label for c in added)
    assert "BUTTON_2_MODIFIER_3" in labels and "BUTTON_1_MODIFIER_5" in labels
    hidden = [c for c in model.cells() if c.element.get("visible") == "0"]
    assert any("button_5" == (c.label or "").lower() for c in hidden)


def test_saved_template_exports_through_both_engines(baked):
    _original, _result, path = baked
    export_device = ExportDeviceLike(
        Template(str(path)), Wrapper("Pickle"), device_with_modifiers()
    )
    legacy = render_template(export_device, None).svg_text
    dom = render_template(export_device, RenderContext(engine_override="dom")).svg_text
    for text in (legacy, dom):
        assert "Gear (LShift)" in text or "Gear (LCtrl)" in text
        assert not re.search(r"\bBUTTON_2_MODIFIER_\d\b", text)
        assert "Pickle" in text and "TEMPLATE_NAME" not in text


def test_store_theme_writes_jd_theme_attribute():
    template = Template(str(STARTER))
    theme = builtin_theme("clean")
    result = bake_template(template, LayoutLayers(), theme=theme, store_theme=True)
    assert result.theme_stored
    doc = TemplateDocument.parse(result.svg_text)
    assert doc.root.get(JD_THEME_ATTRIBUTE)
    assert '"theme_id":"clean"' in doc.root.get(JD_THEME_ATTRIBUTE).replace(" ", "")
    untouched = bake_template(template, LayoutLayers(), theme=theme, store_theme=False)
    assert JD_THEME_ATTRIBUTE not in untouched.svg_text


def test_non_drawio_input_raises_and_filenames_are_sanitised():
    @dataclass
    class Raw:
        raw_data: str

    with pytest.raises(TemplateBakeError):
        bake_template(Raw("BUTTON_1 plain text, not XML"), LayoutLayers())
    assert safe_template_filename('a/b:c*"d') == "a_b_c__d.svg"
    assert safe_template_filename("Mine.SVG") == "Mine.SVG"
    assert safe_template_filename("   ") == "template.svg"
