"""Text measurement and shrink-to-fit for rendered slots (plan §1.2, spike S5).

Why a width table and not Qt
----------------------------
``QFontMetricsF`` needs a ``QGuiApplication`` (``QFontDatabase`` refuses to
load without one), resolves *installed* fonts (``Helvetica`` becomes Nimbus
Sans on Linux and Arial on Windows, so results differ per machine) and is not
something a render worker or a plain unit test should depend on. CSS-only
answers (``line-clamp``, ``overflow: hidden``) clip rather than fit, and a
JavaScript fit pass in the converter would only reach PNG/PDF, leaving the SVG
itself overflowing.

So the measurement is a calibrated table: per-character advance widths (per
mille of the em) read from Liberation Sans Regular/Bold, which is
metric-compatible with Arial, which is metric-compatible with Helvetica — the
family almost every bundled template uses. Other families are scaled relative
to that table (``FAMILY_SCALE``); a small safety factor absorbs hinting and
rendering differences. The result is deterministic, thread-safe and needs no
Qt. The findings are recorded in ``docs/superpowers/specs/2026-10-20-s5-text-fit.md``.

Fitting
-------
``fit_rich`` takes a ``RichText`` (main line plus modifier lines), the box the
label sits in and the font the template/theme decided, then:

1. tries font sizes from the base size down to ``min_size`` in ``SIZE_STEP``
   steps; a size *fits* when every unbreakable word fits the width (words wrap
   at spaces, as Chromium does with ``white-space: normal``) and the wrapped
   block is no taller than the box;
2. at each size, tries draw.io's ``LINE_HEIGHT`` first and then
   ``COMPACT_LINE_HEIGHT`` (tighter leading keeps the glyphs larger, which
   reads better than a smaller font with airy lines);
3. if nothing fits at ``min_size``, drops lines from the end (never the
   protected leading lines) and appends ``+N more`` until the block fits.

Each line is written as its own block (``<div>``) carrying the line's size, so
a line is ``line_height`` × its own size tall (``line_em``: 0.85 for modifier
lines). Mixing sizes *inside* one line box must be avoided: Chromium rounds
each inline box's ascent and descent separately and the union comes out about
a pixel taller than either (measured: 8px lines for 7px text with 0.85em
spans). The fitted size goes on the innermost div itself, so the strut follows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType

from joystick_diagrams.render.binding import MODIFIER_LINE_SIZE_EM, Line, RichText, Run

LINE_HEIGHT = 1.2  # draw.io writes ``line-height: 1.2``
COMPACT_LINE_HEIGHT = 1.0  # second resort before shrinking further
LINE_HEIGHTS = (LINE_HEIGHT, COMPACT_LINE_HEIGHT)
DEFAULT_FONT_SIZE = 12.0  # draw.io's default label size
DEFAULT_MIN_FONT_SIZE = 6.5
SIZE_STEP = 0.5
SAFETY = 1.03  # measured widths are inflated by this much
# The block is centred, so an overshoot this small is half of it per side,
# inside the box stroke (12px VKB hat boxes with two 6.5px lines).
HEIGHT_TOLERANCE_PX = 1.0
UNKNOWN_CHAR_WIDTH = 600  # per mille, for characters outside the table
MORE_LINE_TEXT = "+{count} more"

# fmt: off
# Advance widths, per mille of the em, Liberation Sans (Arial/Helvetica metrics).
_REGULAR = {
    ' ': 278, '!': 278, '"': 355, '#': 556, '$': 556, '%': 889, '&': 667, "'": 191,
    '(': 333, ')': 333, '*': 389, '+': 584, ',': 278, '-': 333, '.': 278, '/': 278,
    '0': 556, '1': 556, '2': 556, '3': 556, '4': 556, '5': 556, '6': 556, '7': 556,
    '8': 556, '9': 556, ':': 278, ';': 278, '<': 584, '=': 584, '>': 584, '?': 556,
    '@': 1015, 'A': 667, 'B': 667, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778,
    'H': 722, 'I': 278, 'J': 500, 'K': 667, 'L': 556, 'M': 833, 'N': 722, 'O': 778,
    'P': 667, 'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722, 'V': 667, 'W': 944,
    'X': 667, 'Y': 667, 'Z': 611, '[': 278, '\\': 278, ']': 278, '^': 469, '_': 556,
    '`': 333, 'a': 556, 'b': 556, 'c': 500, 'd': 556, 'e': 556, 'f': 278, 'g': 556,
    'h': 556, 'i': 222, 'j': 222, 'k': 500, 'l': 222, 'm': 833, 'n': 556, 'o': 556,
    'p': 556, 'q': 556, 'r': 333, 's': 500, 't': 278, 'u': 556, 'v': 500, 'w': 722,
    'x': 500, 'y': 500, 'z': 500, '{': 334, '|': 260, '}': 334, '~': 584, '\xa0': 278,
    '¡': 333, '¢': 556, '£': 556, '¤': 556, '¥': 556, '¦': 260, '§': 556, '¨': 333,
    '©': 737, 'ª': 370, '«': 556, '¬': 584, '\xad': 333, '®': 737, '¯': 552, '°': 400,
    '±': 549, '²': 333, '³': 333, '´': 333, 'µ': 576, '¶': 537, '·': 333, '¸': 333,
    '¹': 333, 'º': 365, '»': 556, '¼': 834, '½': 834, '¾': 834, '¿': 611, 'À': 667,
    'Á': 667, 'Â': 667, 'Ã': 667, 'Ä': 667, 'Å': 667, 'Æ': 1000, 'Ç': 722, 'È': 667,
    'É': 667, 'Ê': 667, 'Ë': 667, 'Ì': 278, 'Í': 278, 'Î': 278, 'Ï': 278, 'Ð': 722,
    'Ñ': 722, 'Ò': 778, 'Ó': 778, 'Ô': 778, 'Õ': 778, 'Ö': 778, '×': 584, 'Ø': 778,
    'Ù': 722, 'Ú': 722, 'Û': 722, 'Ü': 722, 'Ý': 667, 'Þ': 667, 'ß': 611, 'à': 556,
    'á': 556, 'â': 556, 'ã': 556, 'ä': 556, 'å': 556, 'æ': 889, 'ç': 500, 'è': 556,
    'é': 556, 'ê': 556, 'ë': 556, 'ì': 278, 'í': 278, 'î': 278, 'ï': 278, 'ð': 556,
    'ñ': 556, 'ò': 556, 'ó': 556, 'ô': 556, 'õ': 556, 'ö': 556, '÷': 549, 'ø': 611,
    'ù': 556, 'ú': 556, 'û': 556, 'ü': 556, 'ý': 500, 'þ': 556, 'ÿ': 500, '–': 556,
    '—': 1000, '‘': 222, '’': 222, '“': 333, '”': 333, '•': 350, '…': 1000, '€': 556,
}
_BOLD = {
    ' ': 278, '!': 333, '"': 474, '#': 556, '$': 556, '%': 889, '&': 722, "'": 238,
    '(': 333, ')': 333, '*': 389, '+': 584, ',': 278, '-': 333, '.': 278, '/': 278,
    '0': 556, '1': 556, '2': 556, '3': 556, '4': 556, '5': 556, '6': 556, '7': 556,
    '8': 556, '9': 556, ':': 333, ';': 333, '<': 584, '=': 584, '>': 584, '?': 611,
    '@': 975, 'A': 722, 'B': 722, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778,
    'H': 722, 'I': 278, 'J': 556, 'K': 722, 'L': 611, 'M': 833, 'N': 722, 'O': 778,
    'P': 667, 'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722, 'V': 667, 'W': 944,
    'X': 667, 'Y': 667, 'Z': 611, '[': 333, '\\': 278, ']': 333, '^': 584, '_': 556,
    '`': 333, 'a': 556, 'b': 611, 'c': 556, 'd': 611, 'e': 556, 'f': 333, 'g': 611,
    'h': 611, 'i': 278, 'j': 278, 'k': 556, 'l': 278, 'm': 889, 'n': 611, 'o': 611,
    'p': 611, 'q': 611, 'r': 389, 's': 556, 't': 333, 'u': 611, 'v': 556, 'w': 778,
    'x': 556, 'y': 556, 'z': 500, '{': 389, '|': 280, '}': 389, '~': 584, '\xa0': 278,
    '¡': 333, '¢': 556, '£': 556, '¤': 556, '¥': 556, '¦': 280, '§': 556, '¨': 333,
    '©': 737, 'ª': 370, '«': 556, '¬': 584, '\xad': 333, '®': 737, '¯': 552, '°': 400,
    '±': 549, '²': 333, '³': 333, '´': 333, 'µ': 576, '¶': 556, '·': 333, '¸': 333,
    '¹': 333, 'º': 365, '»': 556, '¼': 834, '½': 834, '¾': 834, '¿': 611, 'À': 722,
    'Á': 722, 'Â': 722, 'Ã': 722, 'Ä': 722, 'Å': 722, 'Æ': 1000, 'Ç': 722, 'È': 667,
    'É': 667, 'Ê': 667, 'Ë': 667, 'Ì': 278, 'Í': 278, 'Î': 278, 'Ï': 278, 'Ð': 722,
    'Ñ': 722, 'Ò': 778, 'Ó': 778, 'Ô': 778, 'Õ': 778, 'Ö': 778, '×': 584, 'Ø': 778,
    'Ù': 722, 'Ú': 722, 'Û': 722, 'Ü': 722, 'Ý': 667, 'Þ': 667, 'ß': 611, 'à': 556,
    'á': 556, 'â': 556, 'ã': 556, 'ä': 556, 'å': 556, 'æ': 889, 'ç': 556, 'è': 556,
    'é': 556, 'ê': 556, 'ë': 556, 'ì': 278, 'í': 278, 'î': 278, 'ï': 278, 'ð': 611,
    'ñ': 611, 'ò': 611, 'ó': 611, 'ô': 611, 'õ': 611, 'ö': 611, '÷': 549, 'ø': 611,
    'ù': 611, 'ú': 611, 'û': 611, 'ü': 611, 'ý': 556, 'þ': 611, 'ÿ': 556, '–': 556,
    '—': 1000, '‘': 278, '’': 278, '“': 500, '”': 500, '•': 350, '…': 1000, '€': 556,
}
# fmt: on
REGULAR_WIDTHS = MappingProxyType(_REGULAR)
BOLD_WIDTHS = MappingProxyType(_BOLD)

MONOSPACE_WIDTH = 600  # per mille, every glyph (Courier New / Liberation Mono)
MONOSPACE_FAMILIES = frozenset(
    {"courier new", "courier", "liberation mono", "monospace"}
)

# Average advance relative to Arial for the families the style editor offers
# (measured where installed, else from the vendors' metrics); unknown families
# are assumed a little wider than Arial so the fit stays on the safe side.
FAMILY_SCALE: MappingProxyType[str, float] = MappingProxyType(
    {
        "helvetica": 1.0,
        "arial": 1.0,
        "liberation sans": 1.0,
        "nimbus sans": 1.0,
        "arimo": 1.0,
        "roboto": 1.0,
        "barlow": 1.0,
        "sans-serif": 1.0,
        "verdana": 1.16,
        "dejavu sans": 1.12,
        "tahoma": 1.03,
        "trebuchet ms": 1.02,
        "georgia": 1.08,
        "noto sans": 1.07,
        "atkinson hyperlegible": 1.05,
        "liberation sans narrow": 0.82,
        "arial narrow": 0.82,
        "barlow condensed": 0.78,
    }
)
UNKNOWN_FAMILY_SCALE = 1.05

_WORD_RE = re.compile(r"(\s+)")


# ── Measurement ──


@dataclass(frozen=True)
class FontSpec:
    family: str = "Helvetica"
    size: float = DEFAULT_FONT_SIZE  # px
    bold: bool = False

    def with_size(self, size: float) -> FontSpec:
        return FontSpec(self.family, size, self.bold)


def primary_family(stack: str | None) -> str:
    """First family of a CSS ``font-family`` value, unquoted and lower-cased."""
    first = (stack or "").split(",")[0].strip().strip("'\"").strip()
    return first.lower() or "helvetica"


def family_scale(family: str) -> float:
    return FAMILY_SCALE.get(primary_family(family), UNKNOWN_FAMILY_SCALE)


def text_width(text: str, font: FontSpec, *, size_em: float | None = None) -> float:
    """Width in px of ``text`` set in ``font`` (``size_em`` scales the font size)."""
    family = primary_family(font.family)
    size = font.size * (size_em if size_em is not None else 1.0)
    if family in MONOSPACE_FAMILIES:
        return len(text) * MONOSPACE_WIDTH / 1000 * size * SAFETY
    table = BOLD_WIDTHS if font.bold else REGULAR_WIDTHS
    units = sum(table.get(char, UNKNOWN_CHAR_WIDTH) for char in text)
    return units / 1000 * size * family_scale(family) * SAFETY


def run_width(run: Run, font: FontSpec) -> float:
    run_font = FontSpec(font.family, font.size, font.bold or run.bold)
    return text_width(run.text, run_font, size_em=run.size_em)


def line_width(line: Line, font: FontSpec) -> float:
    return sum(run_width(run, font) for run in line)


# ── Wrapping ──


def _fragments(line: Line) -> list[tuple[Run, str, bool]]:
    """``(run, text, is_space)`` pieces of a line, split at whitespace."""
    pieces: list[tuple[Run, str, bool]] = []
    for run in line:
        for part in _WORD_RE.split(run.text):
            if part:
                pieces.append((run, part, part.isspace()))
    return pieces


def _join_fragments(pieces: list[tuple[Run, str]]) -> Line:
    """Merge consecutive fragments of the same run back into runs."""
    runs: list[Run] = []
    last: Run | None = None
    for run, text in pieces:
        if last is not None and last is run:
            runs[-1] = Run(runs[-1].text + text, run.colour, run.bold, run.size_em)
        else:
            runs.append(Run(text, run.colour, run.bold, run.size_em))
        last = run
    return tuple(runs)


def wrap_line(line: Line, max_width: float | None, font: FontSpec) -> list[Line]:
    """Greedy word wrap at whitespace; a word wider than the box stays whole."""
    if max_width is None:
        return [line] if any(run.text for run in line) else []
    lines: list[Line] = []
    current: list[tuple[Run, str]] = []
    width = 0.0
    for run, text, is_space in _fragments(line):
        piece_width = run_width(Run(text, run.colour, run.bold, run.size_em), font)
        if is_space:
            if current:
                current.append((run, text))
                width += piece_width
            continue
        if current and width + piece_width > max_width:
            lines.append(_join_fragments(_rstrip(current)))
            current, width = [], 0.0
        current.append((run, text))
        width += piece_width
    if current:
        lines.append(_join_fragments(_rstrip(current)))
    return lines


def _rstrip(pieces: list[tuple[Run, str]]) -> list[tuple[Run, str]]:
    while pieces and pieces[-1][1].isspace():
        pieces.pop()
    return pieces


def line_em(line: Line) -> float:
    """The size every run on a line shares (relative to the block), else 1.0."""
    sizes = {run.size_em for run in line}
    if len(sizes) == 1:
        (only,) = sizes
        return only if only is not None else 1.0
    return 1.0


def fits_width(lines: list[Line], max_width: float | None, font: FontSpec) -> bool:
    return max_width is None or all(
        line_width(line, font) <= max_width for line in lines
    )


# ── Fitting ──


@dataclass(frozen=True)
class FitBox:
    width: float | None  # None → unconstrained
    height: float | None


@dataclass(frozen=True)
class FitResult:
    font_size: float
    base_size: float
    lines: tuple[Line, ...]  # the lines to write (possibly truncated + "+N more")
    wrapped: tuple[Line, ...]  # the same lines after word wrap (for ``<text>``)
    truncated: int  # modifier lines dropped
    fits: bool
    line_height: float = LINE_HEIGHT

    @property
    def shrunk(self) -> bool:
        return self.font_size < self.base_size

    @property
    def compact(self) -> bool:
        return self.line_height < LINE_HEIGHT


def _sizes(base: float, minimum: float) -> list[float]:
    sizes = [base]
    size = base
    while size - SIZE_STEP >= minimum:
        size = round(size - SIZE_STEP, 2)
        sizes.append(size)
    if sizes[-1] > minimum:
        sizes.append(minimum)
    return sizes


def _layout(
    lines: tuple[Line, ...], box: FitBox, font: FontSpec, line_height: float
) -> tuple[tuple[Line, ...], bool]:
    wrapped: list[Line] = []
    for line in lines:
        wrapped.extend(wrap_line(line, box.width, font))
    height = sum(line_height * font.size * line_em(line) for line in wrapped)
    fits = fits_width(wrapped, box.width, font) and (
        box.height is None or height <= box.height + HEIGHT_TOLERANCE_PX
    )
    return tuple(wrapped), fits


def _try(
    lines: tuple[Line, ...], box: FitBox, font: FontSpec
) -> tuple[tuple[Line, ...], float] | None:
    """The wrapped lines and line height at which ``lines`` fit, else ``None``."""
    for line_height in LINE_HEIGHTS:
        wrapped, fits = _layout(lines, box, font, line_height)
        if fits:
            return wrapped, line_height
    return None


def more_line(count: int) -> Line:
    return (
        Run(
            MORE_LINE_TEXT.format(count=count), bold=True, size_em=MODIFIER_LINE_SIZE_EM
        ),
    )


def fit_rich(
    rich: RichText,
    box: FitBox,
    font: FontSpec,
    *,
    min_size: float = DEFAULT_MIN_FONT_SIZE,
    protected: int = 1,
) -> FitResult:
    """Shrink, then truncate, ``rich`` so it fits ``box`` (see the module docstring).

    ``protected`` leading lines (the main binding text) are never dropped; at
    least one line always stays.
    """
    lines = rich.lines
    minimum = min(min_size, font.size)
    for size in _sizes(font.size, minimum):
        found = _try(lines, box, font.with_size(size))
        if found is not None:
            return FitResult(size, font.size, lines, found[0], 0, True, found[1])
    small = font.with_size(minimum)
    keep_at_least = max(1, min(protected, len(lines)))
    candidate = lines
    for keep in range(len(lines) - 1, keep_at_least - 1, -1):
        dropped = len(lines) - keep
        candidate = (*lines[:keep], more_line(dropped))
        found = _try(candidate, box, small)
        if found is not None:
            return FitResult(
                minimum, font.size, candidate, found[0], dropped, True, found[1]
            )
    # Nothing fits: write the shortest candidate at the smallest size, compact.
    wrapped, _ = _layout(candidate, box, small, COMPACT_LINE_HEIGHT)
    truncated = 0 if candidate is lines else len(lines) - keep_at_least
    return FitResult(
        minimum, font.size, candidate, wrapped, truncated, False, COMPACT_LINE_HEIGHT
    )


__all__ = [
    "COMPACT_LINE_HEIGHT",
    "DEFAULT_FONT_SIZE",
    "DEFAULT_MIN_FONT_SIZE",
    "FAMILY_SCALE",
    "LINE_HEIGHT",
    "FitBox",
    "FitResult",
    "FontSpec",
    "family_scale",
    "fit_rich",
    "line_em",
    "line_width",
    "more_line",
    "primary_family",
    "text_width",
    "wrap_line",
]

if __name__ == "__main__":
    pass
