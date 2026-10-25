"""Resolve placeholder tokens to text and fill them in one pass.

``BindingResolver`` turns a ``Device_`` plus profile name into *plain visible
text* per token with the same semantics the legacy regex engine has today:

- case-insensitive token lookup;
- ``KEY`` → the resolved command, or ``cmd | mod - key | …`` when merged
  modifiers are enabled (empty parts skipped, as ``export._join_input_parts``);
- ``KEY_MODIFIERS`` → every ``str(mod)`` joined with the separator;
- ``KEY_MODIFIER_N`` → ``str(mod)``; ``_KEY`` → the joined key names;
  ``_ACTION`` → the resolved modifier command;
- ``TEMPLATE_NAME`` / ``CURRENT_DATE``;
- anything unbound, out of range or legacy-only → ``""`` (blanked).

Legacy ``sanitize_string_for_svg`` *unescapes* before escaping (so a DCS
description ``a &amp; b`` shows as ``a & b``). Every value here goes through the
same ``unescape(v, {"&quot;": '"', "&apos;": "'"})`` and is then inserted as
text; lxml escapes once on serialise, so output never contains ``&amp;amp;``.

``fill_text`` is the single-pass replacement: the replacement is a function
(backslashes are literal) and replaced text is never rescanned (``Same as
BUTTON_2`` stays as typed).

Rich text (plan §2.2C/H)
------------------------
``rich_for(token)`` returns the same text as ``text_for`` but structured as
lines of coloured runs: modifier lines under the main text, per-key colours in
``_KEY`` boxes, a ``+N more`` overflow hint. ``rich.plain()`` always equals
``text_for`` (overflow aside), so the fill stage can write plain text and the
presentation hook can rewrite only the slots that need markup.
"""

from __future__ import annotations

import dataclasses
import html
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from xml.sax.saxutils import unescape

from joystick_diagrams.input.modifier import Modifier
from joystick_diagrams.modifier_identity import (
    ModifierDisplay,
    ModifierKeyDisplay,
    ModifierRegistrySnapshot,
    ResolvedModifier,
    ResolvedModifierKey,
    resolve_modifier,
)
from joystick_diagrams.render.slots import SlotRole
from joystick_diagrams.render.tokens import BLANK_RE, TokenInfo, classify

_UNESCAPE_EXTRA = {"&quot;": '"', "&apos;": "'"}
KEY_JOINER = "+"
MODIFIER_LINE_SEPARATOR = " - "


def normalise_value(value: str) -> str:
    """The legacy unescape normalisation applied before any escaping."""
    return unescape(value, _UNESCAPE_EXTRA)


def modifier_key_text(modifier: Modifier) -> str:
    """``+``-joined key names; follows ``Modifier.sorted_keys`` once it exists."""
    keys = getattr(modifier, "sorted_keys", None)
    return KEY_JOINER.join(keys if keys is not None else modifier.modifiers)


def overflow_hint(count: int) -> str:
    return f" +{count} more"


# ── Rich text ──


MODIFIER_LINE_SIZE_EM = 0.85  # modifier lines under the main text are a little smaller


@dataclass(frozen=True)
class Run:
    text: str
    colour: str | None = None  # text colour (#RRGGBB) or None to inherit
    bold: bool = False
    size_em: float | None = None  # relative font size, None to inherit

    @property
    def is_plain(self) -> bool:
        return self.colour is None and not self.bold and self.size_em is None


Line = tuple[Run, ...]


@dataclass(frozen=True)
class RichText:
    lines: tuple[Line, ...]

    def plain(self, separator: str = " | ") -> str:
        return separator.join("".join(run.text for run in line) for line in self.lines)

    @property
    def is_plain(self) -> bool:
        """True when markup would change nothing: one line, no colours, no bold."""
        return len(self.lines) <= 1 and all(
            run.is_plain for line in self.lines for run in line
        )


@dataclass(frozen=True)
class BindingOptions:
    """Export-time settings shared by both engines, snapshotted by the caller."""

    merge_modifiers: bool
    join_separator: str
    date_format: str
    labels: Mapping[str, str] | None = None  # None → no label resolution
    now: datetime | None = None  # None → datetime.now() at resolve time
    modifier_display: ModifierDisplay = ModifierDisplay.TEMPLATE_BOXES
    registry: ModifierRegistrySnapshot | None = None  # None → no colours, raw keys
    overflow_hint: bool = False  # append "+N more" when boxes run out (TEMPLATE_BOXES)


@dataclass
class BindingResolver:
    device: Any  # Device_
    profile_name: str
    options: BindingOptions
    _inputs: dict[str, Any] = field(init=False, repr=False)
    _cache: dict[str, str] = field(init=False, default_factory=dict, repr=False)
    _now: datetime = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._inputs = {
            key.lower(): value
            for key, value in self.device.get_combined_inputs().items()
        }
        self._now = self.options.now or datetime.now()

    # ── Lookup ──

    def resolve_label(self, command: str) -> str:
        labels = self.options.labels
        return labels.get(command, command) if labels is not None else command

    def resolved_modifiers(self, input_obj: Any) -> list[Modifier]:
        return [
            dataclasses.replace(m, command=self.resolve_label(m.command))
            for m in input_obj.modifiers
        ]

    def input_keys(self) -> list[str]:
        return list(self._inputs)

    def modifier_count(self, input_key: str) -> int:
        input_obj = self._inputs.get(input_key.lower())
        return len(input_obj.modifiers) if input_obj is not None else 0

    def modifier_for(self, input_key: str, index: int) -> Modifier | None:
        """The 1-based ``index``-th modifier of an input, with labels resolved."""
        input_obj = self._inputs.get(input_key.lower())
        if input_obj is None:
            return None
        modifiers = self.resolved_modifiers(input_obj)
        if index < 1 or index > len(modifiers):
            return None
        return modifiers[index - 1]

    def text_for(self, token: str) -> str:
        """Plain visible text for a token (``""`` when it must be blanked)."""
        key = token.lower()
        cached = self._cache.get(key)
        if cached is None:
            cached = normalise_value(self._raw_text_for(classify(token)))
            self._cache[key] = cached
        return cached

    def html_for(self, token: str) -> str:
        """Text for an ``html=1`` model label (markup-escaped, quotes kept)."""
        return html.escape(self.text_for(token), quote=False)

    # ── Modifier keys (registry-aware) ──

    def resolve_modifier(self, modifier: Modifier) -> ResolvedModifier | None:
        registry = self.options.registry
        return resolve_modifier(modifier, registry) if registry is not None else None

    def _ordered_keys(
        self, modifier: Modifier, resolved: ResolvedModifier | None
    ) -> list[tuple[str, ResolvedModifierKey | None]]:
        """(raw, resolved key) pairs: registry order for Simplified, rank order otherwise."""
        by_raw = {key.raw: key for key in resolved.keys} if resolved else {}
        simplified = (
            self.options.registry is not None
            and self.options.registry.key_display is ModifierKeyDisplay.SIMPLIFIED
        )
        raws = (
            [key.raw for key in resolved.keys]
            if simplified and resolved
            else list(modifier.sorted_keys)
        )
        return [(raw, by_raw.get(raw)) for raw in raws]

    def key_runs(self, modifier: Modifier) -> Line:
        """``L Ctrl`` ``+`` ``L Shift`` with each key coloured by its own group."""
        resolved = self.resolve_modifier(modifier)
        runs: list[Run] = []
        for index, (raw, key) in enumerate(self._ordered_keys(modifier, resolved)):
            if index:
                runs.append(Run(KEY_JOINER))
            label = key.display_label if key is not None else raw
            runs.append(Run(label, colour=key.text_colour if key else None))
        return tuple(runs)

    def key_text(self, modifier: Modifier) -> str:
        return "".join(run.text for run in self.key_runs(modifier))

    def modifier_line(self, modifier: Modifier) -> str:
        """``str(mod)`` with display labels: ``"Alt Fire - L Shift"``."""
        return f"{modifier.command}{MODIFIER_LINE_SEPARATOR}{self.key_text(modifier)}"

    def modifier_colour(self, modifier: Modifier) -> str | None:
        resolved = self.resolve_modifier(modifier)
        return resolved.text_colour if resolved is not None else None

    def modifier_box_colour(self, modifier: Modifier) -> str | None:
        resolved = self.resolve_modifier(modifier)
        return resolved.colour if resolved is not None else None

    # ── Per-role text (legacy semantics) ──

    def _raw_text_for(self, info: TokenInfo) -> str:
        if info.role is SlotRole.TITLE:
            return self.profile_name
        if info.role is SlotRole.DATE:
            return self._now.strftime(self.options.date_format)
        if info.role is SlotRole.UNKNOWN or info.input_key is None:
            return ""
        input_obj = self._inputs.get(info.input_key)
        if input_obj is None:
            return ""
        if info.role is SlotRole.ACTION:
            return self._action_text(input_obj)
        return self._modifier_text(info, self.resolved_modifiers(input_obj))

    def _join(self, parts: list[str]) -> str:
        return self.options.join_separator.join(part for part in parts if part)

    def _action_text(self, input_obj: Any) -> str:
        command = self.resolve_label(input_obj.command)
        modifiers = self.resolved_modifiers(input_obj)
        if self.options.merge_modifiers and modifiers:
            return self._join([command] + [self.modifier_line(m) for m in modifiers])
        return command

    def _modifier_text(self, info: TokenInfo, modifiers: list[Modifier]) -> str:
        if info.role is SlotRole.MODIFIERS:
            return self._join([self.modifier_line(mod) for mod in modifiers])
        index = info.modifier_index
        if index is None or index < 1 or index > len(modifiers):
            return ""
        modifier = modifiers[index - 1]
        if info.role is SlotRole.MODIFIER_KEY:
            return self.key_text(modifier)
        if info.role is SlotRole.MODIFIER_ACTION:
            return modifier.command
        return self.modifier_line(modifier)

    # ── Rich text per role ──

    def rich_for(self, token: str, overflow: int = 0) -> RichText | None:
        """Structured text for a slot, or ``None`` when plain text is all there is.

        ``overflow`` is the number of modifiers the template had no box for; it
        is only shown under ``TEMPLATE_BOXES`` (the other modes list everything).
        """
        info = classify(token)
        input_obj = self._inputs.get(info.input_key or "")
        if input_obj is None or info.role is SlotRole.UNKNOWN:
            return None
        modifiers = self.resolved_modifiers(input_obj)
        if info.role is SlotRole.ACTION:
            return self._rich_action(input_obj, modifiers, overflow)
        if info.role is SlotRole.MODIFIERS:
            return self._rich_lines([self._modifier_runs(m) for m in modifiers])
        return self._rich_modifier_slot(info, modifiers)

    def _rich_modifier_slot(
        self, info: TokenInfo, modifiers: list[Modifier]
    ) -> RichText | None:
        index = info.modifier_index
        if index is None or index < 1 or index > len(modifiers):
            return None
        modifier = modifiers[index - 1]
        if info.role is SlotRole.MODIFIER_KEY:
            return RichText((self.key_runs(modifier),))
        if info.role is SlotRole.MODIFIER:
            return RichText((self._modifier_runs(modifier),))
        return None  # MODIFIER_ACTION: plain command text

    def _modifier_runs(self, modifier: Modifier) -> Line:
        """``cmd - `` followed by the per-key runs."""
        colour = self.modifier_colour(modifier)
        prefix = Run(f"{modifier.command}{MODIFIER_LINE_SEPARATOR}", colour=colour)
        return (prefix, *self.key_runs(modifier))

    def _rich_lines(self, lines: list[Line]) -> RichText | None:
        """One line per entry under UNDER_MAIN_TEXT, otherwise joined with the separator."""
        lines = [line for line in lines if any(run.text for run in line)]
        if not lines:
            return None
        if self.options.modifier_display is ModifierDisplay.UNDER_MAIN_TEXT:
            return RichText(tuple(lines))
        joined: list[Run] = []
        for index, line in enumerate(lines):
            if index:
                joined.append(Run(self.options.join_separator))
            joined.extend(line)
        return RichText((tuple(joined),))

    def _rich_action(
        self, input_obj: Any, modifiers: list[Modifier], overflow: int
    ) -> RichText | None:
        command = self.resolve_label(input_obj.command)
        if not self.options.merge_modifiers or not modifiers:
            runs: list[Run] = [Run(command)] if command else []
            show_hint = (
                overflow
                and self.options.overflow_hint
                and self.options.modifier_display is ModifierDisplay.TEMPLATE_BOXES
            )
            if show_hint:
                runs.append(Run(overflow_hint(overflow), bold=True))
            return RichText((tuple(runs),)) if runs else None
        lines: list[Line] = [(Run(command),)] if command else []
        under = self.options.modifier_display is ModifierDisplay.UNDER_MAIN_TEXT
        size = MODIFIER_LINE_SIZE_EM if under else None
        for modifier in modifiers:
            colour = self.modifier_colour(modifier)
            text = self.modifier_line(modifier)
            lines.append((Run(text, colour=colour, size_em=size),))
        return self._rich_lines(lines)


# ── Single-pass fill ──


def fill_text(text: str, resolve: Callable[[str], str]) -> str:
    """Replace every BLANK token in ``text`` using ``resolve`` (one pass, no rescans)."""
    return BLANK_RE.sub(lambda match: resolve(match.group(0)), text)


def fill_node_text(element: Any, resolve: Callable[[str], str]) -> None:
    """Fill ``element.text`` and ``element.tail`` in place when they hold tokens."""
    if element.text and BLANK_RE.search(element.text):
        element.text = fill_text(element.text, resolve)
    if element.tail and BLANK_RE.search(element.tail):
        element.tail = fill_text(element.tail, resolve)


if __name__ == "__main__":
    pass
