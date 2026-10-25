import pytest
from lxml import etree

from joystick_diagrams.render.document import (
    TemplateDocument,
    make_parser,
    root_start_offset,
    scan_start_tag,
)
from tests.render.render_fixtures import CORPUS, basic_fixture, build_svg

# lxml hoists namespace declarations before other attributes; this file declares
# xmlns:xlink after style="…" so its root tag is re-ordered (nothing else changes).
NAMESPACE_ORDER_EXCEPTIONS = {"URSA MINOR Fighter Joystick R - Axis POV.svg"}


def test_make_parser_is_fresh_each_call():
    assert make_parser() is not make_parser()


def test_prolog_and_epilog_preserved_verbatim():
    text = build_svg(basic_fixture())
    doc = TemplateDocument.parse(text)
    assert doc.prolog.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<!DOCTYPE svg" in doc.prolog
    assert doc.epilog == "\n"
    out = doc.serialise()
    assert out.startswith(doc.prolog + "<svg")
    assert out.endswith("</svg>\n")


def test_serialise_keeps_width_height_before_content():
    out = TemplateDocument.parse(build_svg(basic_fixture())).serialise()
    head = out[:2000]
    assert head.index('width="400px"') < head.index(' content="')
    assert head.index('height="300px"') < head.index(' content="')


def test_root_start_offset_skips_comments_containing_svg():
    text = '<?xml version="1.0"?>\n<!-- <svg> not the root -->\n<!DOCTYPE svg [ <!ENTITY x "y"> ]>\n<svg/>'
    assert text[root_start_offset(text) :] == "<svg/>"


def test_scan_start_tag_handles_gt_inside_attribute_values():
    text = '<svg a="1>2" content="x&quot;y" b=\'q\'>body</svg>'
    end, spans = scan_start_tag(text, 0)
    assert text[end:] == "body</svg>"
    assert text[slice(*spans["content"])] == '"x&quot;y"'
    assert text[slice(*spans["a"])] == '"1>2"'


def test_not_xml_raises_syntax_error():
    with pytest.raises(etree.XMLSyntaxError):
        TemplateDocument.parse("BUTTON_1 | BUTTON_2 | plain text template")


def test_entity_namespace_svg_parses_with_entities_kept_in_text():
    # Illustrator exports declare xmlns="&ns_svg;" in the internal subset. libxml2
    # expands internal entities inside attribute values even with
    # resolve_entities=False (the plan assumed a parse error), while references in
    # text stay unexpanded. Such files are not draw.io, so they fall back at the
    # model-decode stage instead (see test_render_engine).
    text = (
        '<?xml version="1.0"?>\n<!DOCTYPE svg [<!ENTITY ns_svg "http://www.w3.org/2000/svg">]>\n'
        '<svg xmlns="&ns_svg;"><text>BUTTON_1 &ns_svg;</text></svg>'
    )
    doc = TemplateDocument.parse(text)
    assert doc.root.tag == "{http://www.w3.org/2000/svg}svg"
    assert "&ns_svg;" in doc.serialise()


def test_xxe_entities_are_not_resolved(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP SECRET", encoding="utf-8")
    text = (
        '<?xml version="1.0"?>\n'
        f'<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file://{secret}">]>\n'
        '<svg xmlns="http://www.w3.org/2000/svg"><text>&xxe;</text></svg>'
    )
    doc = TemplateDocument.parse(text)
    assert "TOP SECRET" not in doc.serialise()


def test_copy_is_independent():
    doc = TemplateDocument.parse(build_svg(basic_fixture()))
    clone = doc.copy()
    clone.root.set("data-x", "1")
    assert doc.root.get("data-x") is None
    assert clone.prolog == doc.prolog


@pytest.mark.parametrize("path", CORPUS, ids=lambda p: p.name)
def test_byte_prefix_reproduced_over_corpus(path):
    """Parse + serialise with no edits reproduces everything up to the end of the root start tag."""
    text = path.read_text(encoding="utf-8")
    doc = TemplateDocument.parse(text)
    out = doc.serialise()
    _, tag_end = doc.root_tag_span
    original_head = text[:tag_end]
    if path.name in NAMESPACE_ORDER_EXCEPTIONS:
        out_end, _ = scan_start_tag(out, root_start_offset(out))
        assert sorted(original_head.split()) == sorted(out[:out_end].split())
        assert out.index('width="') < out.index(' content="')
        return
    assert out.startswith(original_head)
    assert out.endswith(doc.epilog)
