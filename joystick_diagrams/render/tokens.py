"""Placeholder grammar for the DOM render engine.

Two token sets exist (plan §4.2):

- **FILL**: the strict grammar that decides which slot a token belongs to
  (``BUTTON_\\d+``, ``AXIS_(SLIDER_\\d+|[A-Z]+)``, ``POV_\\d+_(U|UR|…)``, the
  modifier forms, ``TEMPLATE_NAME`` and ``CURRENT_DATE``).
- **BLANK**: everything the legacy regex engine blanks, i.e. a superset of
  FILL and of ``Template.BUTTON_KEY``/``AXIS_KEY``/``HAT_KEY``/``MODIFIER_KEYS``.
  Corpus tokens such as ``POV_1_LL`` or ``BUTTON_1_MODIFIER_1_STYLE`` are not
  fillable but must still disappear from the output exactly as today.

``BLANK_RE`` is the single word-bounded, case-insensitive alternation used by
the single-pass fill (``binding.fill_text``). ``classify`` turns a matched
token into its structural ``SlotRole`` so the resolver knows what to emit.
``Template``'s own regexes are not touched (plan §4.4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from joystick_diagrams.render.slots import SlotRole

# ── FILL grammar ──

_HAT_DIRECTIONS = "UR|UL|DR|DL|U|R|D|L"
INPUT_KEY_PATTERN = (
    rf"(?:BUTTON_\d+|AXIS_[A-Za-z]+(?:_\d+)?|POV_\d+_(?:{_HAT_DIRECTIONS}))"
)

FILL_PATTERNS: tuple[str, ...] = (
    rf"{INPUT_KEY_PATTERN}_MODIFIER_\d+_(?:KEY|ACTION)",
    rf"{INPUT_KEY_PATTERN}_MODIFIER_\d+",
    rf"{INPUT_KEY_PATTERN}_MODIFIERS",
    INPUT_KEY_PATTERN,
    r"TEMPLATE_NAME",
    r"CURRENT_DATE",
)

# ── Legacy blanking patterns (template.py:18-31, export.py:233-252) ──
# AXIS is widened from ``_?\d?+`` to ``_?\d*`` so multi-digit sliders are
# blanked too; everything legacy matches is still matched.
LEGACY_PATTERNS: tuple[str, ...] = (
    r"[a-zA-Z]+_\w+_Modifier_\d+_[a-zA-Z]+",
    r"[a-zA-Z]+_\w+_Modifier_\d+",
    r"[a-zA-Z]+_\w+_Modifiers",
    r"BUTTON_\d+",
    r"AXIS_[a-zA-Z]+_?\d*",
    r"POV_\d+_[URDL]+",
)

FILL_RE = re.compile(r"\b(?:" + "|".join(FILL_PATTERNS) + r")\b", re.IGNORECASE)
BLANK_RE = re.compile(
    r"\b(?:" + "|".join(FILL_PATTERNS + LEGACY_PATTERNS) + r")\b", re.IGNORECASE
)

_CLASSIFY_RE = re.compile(
    rf"^(?P<input>{INPUT_KEY_PATTERN})"
    r"(?:_MODIFIER(?:(?P<all>S)|_(?P<n>\d+)(?:_(?P<suffix>KEY|ACTION))?))?$",
    re.IGNORECASE,
)
_LEGACY_INPUT_RE = re.compile(r"^(?P<input>[a-zA-Z]+_\w+?)_Modifier", re.IGNORECASE)


@dataclass(frozen=True)
class TokenInfo:
    token: str  # lower-cased token text
    role: SlotRole
    input_key: str | None  # lower-cased
    modifier_index: int | None

    @property
    def fillable(self) -> bool:
        return self.role is not SlotRole.UNKNOWN


def _modifier_role(match: re.Match[str]) -> tuple[SlotRole, int | None]:
    if match.group("all"):
        return SlotRole.MODIFIERS, None
    index = int(match.group("n"))
    suffix = (match.group("suffix") or "").upper()
    if suffix == "KEY":
        return SlotRole.MODIFIER_KEY, index
    if suffix == "ACTION":
        return SlotRole.MODIFIER_ACTION, index
    return SlotRole.MODIFIER, index


def classify(token: str) -> TokenInfo:
    """Classify a token matched by ``BLANK_RE`` (case-insensitive)."""
    lowered = token.lower()
    if lowered == "template_name":
        return TokenInfo(lowered, SlotRole.TITLE, None, None)
    if lowered == "current_date":
        return TokenInfo(lowered, SlotRole.DATE, None, None)

    match = _CLASSIFY_RE.match(token)
    if match is None:
        legacy = _LEGACY_INPUT_RE.match(token)
        input_key = legacy.group("input").lower() if legacy else None
        return TokenInfo(lowered, SlotRole.UNKNOWN, input_key, None)

    input_key = match.group("input").lower()
    if match.group("n") is None and match.group("all") is None:
        return TokenInfo(lowered, SlotRole.ACTION, input_key, None)
    role, index = _modifier_role(match)
    return TokenInfo(lowered, role, input_key, index)


def find_tokens(text: str) -> list[str]:
    """All BLANK tokens in ``text``, lower-cased, in order."""
    return [m.lower() for m in BLANK_RE.findall(text)]


if __name__ == "__main__":
    pass
