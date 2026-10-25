"""Decode, edit and re-encode the draw.io model stored in the SVG ``content`` attribute.

draw.io writes ``<mxfile><diagram>…</diagram></mxfile>`` into the root
``content="…"`` attribute. The diagram payload is either a plain
``<mxGraphModel>`` child or a compressed string (base64 → raw deflate →
URL-encoded XML). ``DrawioModel.from_content`` accepts both; ``to_content``
always writes the model back **uncompressed** (draw.io reads both forms and
nothing else reads ``content=``), which is what lets the exported file reopen
in draw.io with the filled text (fixes legacy bugs 1 and 2).

``MxCell`` is a thin view over an ``<mxCell>`` element and its optional
``<object>``/``<UserObject>`` wrapper (whose ``label`` attribute carries the
text). ``parse_style``/``format_style`` round-trip draw.io style strings while
preserving key order, so later style writing can edit a single key safely.
"""

from __future__ import annotations

import base64
import binascii
import re
import urllib.parse
import zlib
from dataclasses import dataclass

from lxml import etree

from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.slots import Rect

WRAPPER_TAGS = frozenset({"object", "UserObject"})
_HTML_TAG_RE = re.compile(r"<[^>]+>")


class ModelDecodeError(ValueError):
    """The ``content`` attribute is missing, not draw.io, or cannot be decoded."""


# ── Style strings ──


def parse_style(style: str | None) -> dict[str, str | None]:
    """``"rounded=1;html=1;shape"`` → ``{"rounded": "1", "html": "1", "shape": None}``."""
    result: dict[str, str | None] = {}
    for part in (style or "").split(";"):
        if not part:
            continue
        key, sep, value = part.partition("=")
        result[key] = value if sep else None
    return result


def format_style(style: dict[str, str | None]) -> str:
    """Inverse of ``parse_style``; every entry is terminated by ``;`` like draw.io does."""
    parts = [key if value is None else f"{key}={value}" for key, value in style.items()]
    return "".join(f"{part};" for part in parts)


# ── Cells ──


def _float_attr(element: etree._Element, name: str) -> float:
    value = element.get(name)
    try:
        return float(value) if value is not None else 0.0
    except ValueError:
        return 0.0


@dataclass
class MxCell:
    element: etree._Element
    wrapper: etree._Element | None = None

    @property
    def id(self) -> str | None:  # noqa: A003
        holder = self.wrapper if self.wrapper is not None else self.element
        return holder.get("id")

    @property
    def parent(self) -> str | None:
        return self.element.get("parent")

    @property
    def style(self) -> str:
        return self.element.get("style") or ""

    @property
    def style_dict(self) -> dict[str, str | None]:
        return parse_style(self.style)

    def set_style_dict(self, style: dict[str, str | None]) -> None:
        self.element.set("style", format_style(style))

    @property
    def is_vertex(self) -> bool:
        return self.element.get("vertex") == "1"

    @property
    def is_edge(self) -> bool:
        return self.element.get("edge") == "1"

    @property
    def source(self) -> str | None:
        return self.element.get("source")

    @property
    def target(self) -> str | None:
        return self.element.get("target")

    @property
    def visible(self) -> bool:
        return self.element.get("visible") != "0"

    @property
    def is_html(self) -> bool:
        return self.style_dict.get("html") == "1"

    @property
    def rotation(self) -> float:
        value = self.style_dict.get("rotation")
        try:
            return float(value) if value else 0.0
        except ValueError:
            return 0.0

    @property
    def label(self) -> str:
        if self.wrapper is not None:
            return self.wrapper.get("label") or ""
        return self.element.get("value") or ""

    def set_label(self, value: str) -> None:
        if self.wrapper is not None:
            self.wrapper.set("label", value)
        else:
            self.element.set("value", value)

    @property
    def tooltip(self) -> str | None:
        return self.wrapper.get("tooltip") if self.wrapper is not None else None

    def set_tooltip(self, value: str) -> None:
        if self.wrapper is not None:
            self.wrapper.set("tooltip", value)

    @property
    def plain_label(self) -> str:
        """Label with HTML tags stripped and entities decoded (for alignment/compare)."""
        import html

        text = self.label
        if self.is_html:
            text = html.unescape(_HTML_TAG_RE.sub(" ", text))
        return " ".join(text.split())

    @property
    def geometry(self) -> Rect | None:
        geo = self.element.find("mxGeometry")
        if geo is None:
            return None
        return Rect(
            _float_attr(geo, "x"),
            _float_attr(geo, "y"),
            _float_attr(geo, "width"),
            _float_attr(geo, "height"),
        )


# ── Model ──


def _decode_compressed(payload: str) -> etree._Element:
    try:
        raw = base64.b64decode(payload.strip(), validate=True)
        inflated = zlib.decompress(raw, -15)
    except (binascii.Error, zlib.error, ValueError) as e:
        raise ModelDecodeError(f"Compressed diagram could not be inflated: {e}") from e
    xml = urllib.parse.unquote(inflated.decode("utf-8", errors="replace"))
    try:
        return etree.fromstring(xml.encode("utf-8"), make_parser())
    except etree.XMLSyntaxError as e:
        raise ModelDecodeError(f"Inflated diagram is not XML: {e}") from e


@dataclass
class DrawioModel:
    mxfile: etree._Element | None  # None when content held a bare <mxGraphModel>
    diagram: etree._Element | None
    graph: etree._Element
    was_compressed: bool

    @classmethod
    def from_content(cls, content: str | None) -> DrawioModel:
        if not content:
            raise ModelDecodeError("No content attribute")
        try:
            root = etree.fromstring(content.encode("utf-8"), make_parser())
        except etree.XMLSyntaxError as e:
            raise ModelDecodeError(f"content attribute is not XML: {e}") from e

        tag = etree.QName(root).localname
        if tag == "mxGraphModel":
            return cls(None, None, root, was_compressed=False)
        if tag != "mxfile":
            raise ModelDecodeError(f"content root is <{tag}>, not <mxfile>")

        diagram = root.find("diagram")
        if diagram is None:
            raise ModelDecodeError("<mxfile> has no <diagram>")
        graph = diagram.find("mxGraphModel")
        if graph is not None:
            return cls(root, diagram, graph, was_compressed=False)
        graph = _decode_compressed(diagram.text or "")
        if etree.QName(graph).localname != "mxGraphModel":
            raise ModelDecodeError("Compressed diagram does not hold an <mxGraphModel>")
        return cls(root, diagram, graph, was_compressed=True)

    def cells(self) -> list[MxCell]:
        """All ``<mxCell>`` elements in document order, with their wrappers."""
        result: list[MxCell] = []
        for element in self.graph.iter("mxCell"):
            parent = element.getparent()
            wrapper = (
                parent
                if parent is not None and etree.QName(parent).localname in WRAPPER_TAGS
                else None
            )
            result.append(MxCell(element, wrapper))
        return result

    def cells_by_id(self) -> dict[str, MxCell]:
        return {cell.id: cell for cell in self.cells() if cell.id is not None}

    def root_attributes(self) -> dict[str, str]:
        """Attributes of a wrapped root cell (``<object id="0" jd_theme="…">``)."""
        for cell in self.cells():
            if cell.id == "0" and cell.wrapper is not None:
                return {k: v for k, v in cell.wrapper.attrib.items() if k != "id"}
        return {}

    def to_content(self) -> str:
        """Serialise the model, always uncompressed."""
        if self.mxfile is None:
            return etree.tostring(self.graph, encoding="unicode")
        if self.was_compressed and self.diagram is not None:
            self.diagram.text = None
            for child in list(self.diagram):
                self.diagram.remove(child)
            self.diagram.append(self.graph)
            self.was_compressed = False
        return etree.tostring(self.mxfile, encoding="unicode")


if __name__ == "__main__":
    pass
