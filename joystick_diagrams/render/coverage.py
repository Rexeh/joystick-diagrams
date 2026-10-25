"""Token coverage check: would the DOM engine fill everything legacy would?

The legacy regexes (``Template.*_KEY`` and the ``replace_unused_keys`` set) are
counted over the raw template text outside the prolog and the ``content``
attribute (the model is filled separately), minus comments and processing
instructions. The same regexes are counted over every DOM text node (element
text plus every tail). A difference means a token sits somewhere the DOM
engine does not touch (an attribute, the DOCTYPE …) and the export must fall
back to the legacy engine (plan §1.5 trigger 3).

Base64 ``data:`` URIs make up most of a large template. Standard base64 has no
underscore and every legacy token needs one, so underscore-free data URIs are
removed before counting; any data URI that does contain ``_`` is still scanned.
"""

from __future__ import annotations

import re
from typing import Any

from lxml import etree

from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.template import Template

LEGACY_REGEXES: tuple[re.Pattern[str], ...] = (
    Template.BUTTON_KEY,
    Template.AXIS_KEY,
    Template.HAT_KEY,
    *Template.MODIFIER_KEYS,
    Template.TEMPLATE_NAMING_KEY,
    Template.TEMPLATE_DATE_KEY,
)
_DATA_URI_RE = re.compile(r'"data:[^"_]*"')


def count_legacy_tokens(text: str | None) -> int:
    if not text:
        return 0
    return sum(len(pattern.findall(text)) for pattern in LEGACY_REGEXES)


def strip_data_uris(text: str) -> str:
    return _DATA_URI_RE.sub('""', text)


def _is_element(node: Any) -> bool:
    return isinstance(node.tag, str)


def count_dom_tokens(doc: TemplateDocument) -> int:
    """Tokens in every text node the fill stage visits."""
    total = 0
    for node in doc.root.iter():
        if _is_element(node):
            total += count_legacy_tokens(node.text)
        total += count_legacy_tokens(node.tail)
    return total


def count_expected_tokens(doc: TemplateDocument) -> int:
    """Tokens legacy would replace outside the model: root tag (sans content) + body."""
    total = count_legacy_tokens(doc.raw_root_tag_without_content)
    total += count_legacy_tokens(strip_data_uris(doc.raw_body))
    for node in doc.root.iter(etree.Comment, etree.ProcessingInstruction):
        total -= count_legacy_tokens(node.text)
    return total


def coverage_mismatch(doc: TemplateDocument) -> str | None:
    """None when counts agree, otherwise a reason string."""
    expected = count_expected_tokens(doc)
    actual = count_dom_tokens(doc)
    if expected == actual:
        return None
    return f"legacy regexes see {expected} token(s) in the body, DOM text nodes hold {actual}"


if __name__ == "__main__":
    pass
