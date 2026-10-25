import pytest

from joystick_diagrams.render.adapters import (
    DrawioCellIdAdapter,
    DrawioOrderedAdapter,
    TextOnlyAdapter,
    detect_adapter,
)
from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.slots import Capability, SlotRole, TextTargetKind
from tests.render.render_fixtures import (
    CORPUS,
    RENDER_OFFSET,
    CellSpec,
    DrawioFixture,
    basic_fixture,
    build_svg,
)


def _slots(fx: DrawioFixture):
    doc = TemplateDocument.parse(build_svg(fx))
    model = DrawioModel.from_content(doc.root.get("content"))
    adapter = detect_adapter(doc, model)
    return adapter, adapter.build_slots(doc, model)


@pytest.mark.parametrize(
    ("variant", "adapter_type"),
    [
        ("flat", DrawioOrderedAdapter),
        ("grouped", DrawioOrderedAdapter),
        ("cellid", DrawioCellIdAdapter),
    ],
)
def test_detection_and_full_alignment(variant, adapter_type):
    adapter, slot_map = _slots(basic_fixture(variant))
    assert isinstance(adapter, adapter_type)
    by_token = slot_map.by_token
    assert set(by_token) == {
        "template_name",
        "current_date",
        "button_1",
        "button_1_modifier_1",
        "button_1_modifier_1_key",
        "button_1_modifier_1_action",
        "button_1_modifiers",
        "button_2",
        "axis_x",
        "pov_1_u",
        "pov_1_ll",
    }
    for slot in slot_map.slots:
        assert slot.cell is not None, slot.key
        assert slot.cell.plain_label.lower() == slot.key
        assert slot.shape is not None and slot.bbox is not None
        kinds = {target.kind for target in slot.text_targets}
        assert kinds == {TextTargetKind.FOREIGN_OBJECT, TextTargetKind.TEXT}
    assert slot_map.offset == RENDER_OFFSET
    assert Capability.LAYOUT in slot_map.capabilities
    assert Capability.EDGES in slot_map.capabilities


def test_roles_and_indexes():
    _, slot_map = _slots(basic_fixture())
    by_token = slot_map.by_token
    assert by_token["button_1"][0].role is SlotRole.ACTION
    assert by_token["button_1_modifier_1_key"][0].role is SlotRole.MODIFIER_KEY
    assert by_token["button_1_modifier_1_key"][0].modifier_index == 1
    assert by_token["button_1_modifiers"][0].role is SlotRole.MODIFIERS
    assert by_token["template_name"][0].role is SlotRole.TITLE
    assert by_token["pov_1_ll"][0].role is SlotRole.UNKNOWN
    assert slot_map.modifier_box_count("BUTTON_1") == 1


@pytest.mark.parametrize("variant", ["flat", "cellid"])
def test_edges_attached_to_both_ends(variant):
    _, slot_map = _slots(basic_fixture(variant))
    by_token = slot_map.by_token
    for key in ("button_1", "button_1_modifier_1"):
        edges = by_token[key][0].edges
        assert len(edges) == 1
        assert (edges[0].source_id, edges[0].target_id) == ("b1", "b1m1")
        if variant == "cellid":
            assert edges[0].element is not None


def test_multi_token_label_is_one_slot_with_two_tokens():
    fx = DrawioFixture(
        cells=[
            CellSpec(
                "m", "BUTTON_62<br>BUTTON_35", rendered_html="BUTTON_62<br/>BUTTON_35"
            )
        ]
    )
    _, slot_map = _slots(fx)
    assert len(slot_map.slots) == 1
    assert slot_map.slots[0].tokens == ("button_62", "button_35")
    assert set(slot_map.by_token) == {"button_62", "button_35"}


def test_hidden_cells_are_skipped_in_alignment():
    fx = basic_fixture()
    fx.cells.insert(2, CellSpec("hidden", "BUTTON_1", visible=False))
    _, slot_map = _slots(fx)
    slot = slot_map.by_token["button_1"][0]
    assert slot.cell.id == "b1"


def test_shape_dropped_when_geometry_does_not_validate():
    fx = basic_fixture()
    # a shape-less label following another cell's rect would be mis-attributed
    fx.cells.append(CellSpec("free", "BUTTON_9", 300, 250, shape="none"))
    _, slot_map = _slots(fx)
    slot = slot_map.by_token["button_9"][0]
    assert slot.cell is not None
    assert slot.shape is None
    assert slot.bbox is not None  # geometry + offset
    assert (slot.bbox.x, slot.bbox.y) == (
        300 + RENDER_OFFSET[0],
        250 + RENDER_OFFSET[1],
    )


def test_text_only_when_model_has_no_labels():
    fx = DrawioFixture(cells=[CellSpec("x", "")])
    doc = TemplateDocument.parse(build_svg(fx).replace(">x<", ">BUTTON_1<"))
    model = DrawioModel.from_content(doc.root.get("content"))
    assert isinstance(detect_adapter(doc, model), TextOnlyAdapter)


def test_ordered_adapter_degrades_when_nothing_aligns():
    fx = basic_fixture()
    for cell in fx.cells:
        cell.value = cell.value.lower() + "_zzz"  # model labels differ from rendered
    text = build_svg(fx)
    doc = TemplateDocument.parse(text)
    model = DrawioModel.from_content(doc.root.get("content"))
    for cell in model.cells():
        cell.set_label("different")
    slot_map = DrawioOrderedAdapter().build_slots(doc, model)
    assert slot_map.capabilities == {Capability.TEXT, Capability.TEXT_STYLE}
    assert slot_map.notices


@pytest.mark.parametrize("path", CORPUS, ids=lambda p: p.name)
def test_corpus_every_placeholder_label_is_a_slot(path):
    doc = TemplateDocument.parse(path.read_text(encoding="utf-8"))
    model = DrawioModel.from_content(doc.root.get("content"))
    adapter = detect_adapter(doc, model)
    slot_map = adapter.build_slots(doc, model)
    assert slot_map.slots
    assert Capability.SHAPE_STYLE in slot_map.capabilities, slot_map.notices
    aligned = sum(1 for slot in slot_map.slots if slot.cell is not None)
    if isinstance(adapter, DrawioCellIdAdapter):
        assert aligned == len(slot_map.slots)
    else:
        assert aligned / len(slot_map.slots) >= 0.9, slot_map.notices
