"""Hardened lxml parsing and byte-faithful serialisation of a template.

``TemplateDocument.parse`` creates a **new** parser for every parse
(``make_parser``); lxml parsers are not thread-safe and the export worker and
preview runnables must never share one. Entities are never resolved and no
network access is allowed, so untrusted community templates cannot XXE.
``huge_tree`` is required for the 1.3 MB base64 image attributes in the corpus
and is safe because internal entity expansion is disabled.

The prolog (XML declaration, leading comment, DOCTYPE) is kept as the original
text and re-attached verbatim on ``serialise()``; lxml would otherwise move the
comment after the DOCTYPE and normalise the declaration. Root attribute order is
preserved by lxml, so ``width``/``height`` stay before ``content=`` and
``export_image.parse_svg_dimensions`` keeps working.
"""

from __future__ import annotations

import codecs
import copy
import re
from dataclasses import dataclass

from lxml import etree

_ENCODING_DECL_RE = re.compile(rb'^<\?xml[^>]*encoding=["\']([A-Za-z0-9._-]+)["\']')


def make_parser(*, encoding: str | None = None) -> etree.XMLParser:
    """A fresh hardened parser. Never cache or share the result."""
    return etree.XMLParser(
        huge_tree=True,
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        remove_blank_text=False,
        strip_cdata=False,
        encoding=encoding,
    )


_NAME_RE = re.compile(r"[^\s=/>]+")
_BOM = "﻿"


def _skip_doctype(text: str, start: int) -> int:
    """Return the index just past a ``<!DOCTYPE …>`` that may hold an internal subset."""
    depth = 0
    quote: str | None = None
    for i in range(start, len(text)):
        char = text[i]
        if quote is not None:
            if char == quote:
                quote = None
            continue
        if char in ('"', "'"):
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        elif char == ">" and depth == 0:
            return i + 1
    raise ValueError("Unterminated DOCTYPE")


def root_start_offset(text: str) -> int:
    """Index of the root element's start tag (just after the prolog)."""
    i = len(_BOM) if text.startswith(_BOM) else 0
    n = len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if text.startswith("<?", i):
            i = text.index("?>", i) + 2
        elif text.startswith("<!--", i):
            i = text.index("-->", i) + 3
        elif text.startswith("<!", i):
            i = _skip_doctype(text, i)
        elif text.startswith("<", i):
            return i
        else:
            raise ValueError("Content before the root element is not markup")
    raise ValueError("No root element found")


def _skip_space(text: str, i: int) -> int:
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def scan_start_tag(text: str, start: int) -> tuple[int, dict[str, tuple[int, int]]]:
    """Index just past the start tag at ``start`` and the span of every attribute value.

    Spans include the quotes. Attribute values cannot contain their own quote
    character unescaped, so this is exact even when a value holds ``>``.
    """
    name = _NAME_RE.match(text, start + 1)
    if name is None:
        raise ValueError("Malformed start tag")
    i = name.end()
    spans: dict[str, tuple[int, int]] = {}
    while i < len(text):
        i = _skip_space(text, i)
        if text.startswith("/>", i):
            return i + 2, spans
        if text.startswith(">", i):
            return i + 1, spans
        attr = _NAME_RE.match(text, i)
        if attr is None:
            raise ValueError("Malformed attribute")
        i = _skip_space(text, attr.end())
        if not text.startswith("=", i):
            raise ValueError(f"Attribute {attr.group(0)} has no value")
        i = _skip_space(text, i + 1)
        quote = text[i]
        if quote not in ('"', "'"):
            raise ValueError("Unquoted attribute value")
        close = text.index(quote, i + 1)
        spans[attr.group(0)] = (i, close + 1)
        i = close + 1
    raise ValueError("Unterminated start tag")


def _declared_encoding(raw: bytes) -> str | None:
    match = _ENCODING_DECL_RE.match(raw.lstrip(codecs.BOM_UTF8))
    return match.group(1).decode("ascii").lower() if match else None


@dataclass
class TemplateDocument:
    root: etree._Element
    prolog: str
    epilog: str
    raw_text: str  # the original text, for the coverage check
    root_tag_span: tuple[int, int]  # [start, end) of the root start tag in raw_text
    content_span: (
        tuple[int, int] | None
    )  # span of the content="…" value, quotes included

    @classmethod
    def parse(cls, raw: str | bytes) -> TemplateDocument:
        """Parse a template. Raises ``etree.XMLSyntaxError``/``ValueError`` on bad input.

        ``Template.raw_data`` is text read as UTF-8, so a ``str`` is encoded back
        to UTF-8 and the declared encoding is overridden to match.
        """
        if isinstance(raw, str):
            data = raw.encode("utf-8")
            text = raw
            declared = _declared_encoding(data)
            override = "utf-8" if declared not in (None, "utf-8", "utf8") else None
        else:
            data = raw
            text = raw.decode("utf-8", errors="replace")
            override = None

        root = etree.fromstring(data, make_parser(encoding=override))
        start = root_start_offset(text)
        tag_end, spans = scan_start_tag(text, start)
        stripped = text.rstrip()
        return cls(
            root=root,
            prolog=text[:start],
            epilog=text[len(stripped) :],
            raw_text=text,
            root_tag_span=(start, tag_end),
            content_span=spans.get("content"),
        )

    @property
    def raw_body(self) -> str:
        """Original text after the root start tag (no prolog, no root attributes)."""
        return self.raw_text[self.root_tag_span[1] :]

    @property
    def raw_root_tag_without_content(self) -> str:
        """The root start tag text with the ``content`` attribute value removed."""
        start, end = self.root_tag_span
        if self.content_span is None:
            return self.raw_text[start:end]
        c_start, c_end = self.content_span
        return self.raw_text[start:c_start] + self.raw_text[c_end:end]

    def copy(self) -> TemplateDocument:
        """A deep copy for per-render mutation (the batch cache keeps pristine docs)."""
        return TemplateDocument(
            root=copy.deepcopy(self.root),
            prolog=self.prolog,
            epilog=self.epilog,
            raw_text=self.raw_text,
            root_tag_span=self.root_tag_span,
            content_span=self.content_span,
        )

    def serialise(self) -> str:
        """Original prolog + lxml-serialised root + original trailing whitespace."""
        body = etree.tostring(self.root, encoding="unicode", with_tail=False)
        return f"{self.prolog}{body}{self.epilog}"

    def iter_body_nodes(self):
        """Every node under the root, including comments and PIs (their tails are text)."""
        return self.root.iter()


if __name__ == "__main__":
    pass
