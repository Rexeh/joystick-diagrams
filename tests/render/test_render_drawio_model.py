import pytest
from lxml import etree

from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.drawio_model import (
    DrawioModel,
    ModelDecodeError,
    format_style,
    parse_style,
)
from tests.render.render_fixtures import (
    CORPUS,
    CellSpec,
    DrawioFixture,
    basic_fixture,
    build_svg,
)


def _model(fx: DrawioFixture) -> DrawioModel:
    doc = TemplateDocument.parse(build_svg(fx))
    return DrawioModel.from_content(doc.root.get("content"))


def test_plain_model_decodes():
    model = _model(basic_fixture())
    assert not model.was_compressed
    labels = [cell.label for cell in model.cells()]
    assert "BUTTON_1" in labels
    assert "BUTTON_1_Modifier_1_Key" in labels


def test_compressed_model_decodes_and_writes_back_uncompressed():
    model = _model(basic_fixture(compressed=True))
    assert model.was_compressed
    assert [c.label for c in model.cells() if c.label == "BUTTON_1"]
    content = model.to_content()
    assert "<mxGraphModel" in content
    again = DrawioModel.from_content(content)
    assert not again.was_compressed
    assert [c.label for c in again.cells()] == [c.label for c in model.cells()]


def test_roundtrip_label_edit_survives_reencode():
    model = _model(basic_fixture())
    cell = model.cells_by_id()["b1"]
    cell.set_label('Fire & "Forget" <now>')
    content = model.to_content()
    assert (
        DrawioModel.from_content(content).cells_by_id()["b1"].label
        == 'Fire & "Forget" <now>'
    )


def test_wrapper_label_and_tooltip():
    fx = DrawioFixture(
        cells=[
            CellSpec("u", "BUTTON_1", wrapper="UserObject", tooltip="tip BUTTON_1"),
            CellSpec("o", "BUTTON_2", wrapper="object"),
        ]
    )
    model = _model(fx)
    cells = model.cells_by_id()
    assert cells["u"].wrapper is not None
    assert cells["u"].label == "BUTTON_1"
    assert cells["u"].tooltip == "tip BUTTON_1"
    cells["u"].set_label("x")
    assert cells["u"].wrapper.get("label") == "x"
    assert cells["o"].label == "BUTTON_2"


def test_geometry_style_flags():
    model = _model(basic_fixture())
    cell = model.cells_by_id()["b1"]
    assert cell.geometry.x == 10 and cell.geometry.y == 50
    assert cell.is_vertex and not cell.is_edge and cell.is_html and cell.visible
    edge = model.cells_by_id()["e1"]
    assert edge.is_edge and edge.source == "b1" and edge.target == "b1m1"


def test_plain_label_strips_html():
    fx = DrawioFixture(
        cells=[
            CellSpec(
                "h",
                '<span style="x">Button_18</span>&nbsp;x',
                rendered_html='<span style="x">Button_18</span> x',
            )
        ]
    )
    assert _model(fx).cells_by_id()["h"].plain_label == "Button_18 x"


@pytest.mark.parametrize(
    "content",
    [
        "",
        "<notxml",
        "<svg/>",
        "<mxfile/>",
        "<mxfile><diagram>not base64!!</diagram></mxfile>",
    ],
)
def test_decode_failures(content):
    with pytest.raises(ModelDecodeError):
        DrawioModel.from_content(content)


def test_bare_mxgraphmodel_content():
    model = DrawioModel.from_content(
        '<mxGraphModel><root><mxCell id="0"/></root></mxGraphModel>'
    )
    assert model.mxfile is None
    assert model.to_content().startswith("<mxGraphModel")


def test_parse_format_style_roundtrip_preserves_order():
    style = "shape;rounded=1;whiteSpace=wrap;html=1;fontStyle=12;"
    parsed = parse_style(style)
    assert list(parsed) == ["shape", "rounded", "whiteSpace", "html", "fontStyle"]
    assert parsed["shape"] is None
    assert parsed["fontStyle"] == "12"
    assert format_style(parsed) == style
    parsed["strokeColor"] = "#ff0000"
    assert format_style(parsed).endswith("strokeColor=#ff0000;")


@pytest.mark.parametrize("path", CORPUS, ids=lambda p: p.name)
def test_corpus_models_decode(path):
    doc = TemplateDocument.parse(path.read_text(encoding="utf-8"))
    model = DrawioModel.from_content(doc.root.get("content"))
    assert model.cells()
    etree.fromstring(model.to_content().encode())
