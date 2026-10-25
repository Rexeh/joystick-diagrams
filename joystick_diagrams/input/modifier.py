"""Basic modifier structure for the Joystick Diagrams input library.

A ``Modifier`` is an alternative binding for an input that applies when a set
of modifier keys is held. Plugins emit the game's own key vocabulary (``LShift``,
``lalt``, ``JOY_BTN3``...); the application normalises, orders and styles the
keys at export time. Nothing here depends on the database or the UI, so plugins
can import from this module freely.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum


class ModifierKind(str, Enum):
    """What a ``Modifier``'s key set represents.

    ``KEY`` is a real modifier key (or another device's button) the user holds.
    ``QUALIFIER`` is a synthetic label the application promoted during a merge:
    a parent profile name, an aliased device name or a route qualifier such as
    ``Long``. Qualifiers are never aliased to keyboard keys and never coloured.
    """

    KEY = "KEY"
    QUALIFIER = "QUALIFIER"


# ── Built-in key ordering ──────────────────────────────────────────────

# Rank of the side-stripped, casefolded key name. Anything not listed is 4.
_KEY_RANK: dict[str, int] = {
    "ctrl": 0,
    "control": 0,
    "alt": 1,
    "shift": 2,
    "win": 3,
    "meta": 3,
    "super": 3,
    "cmd": 3,
}
_OTHER_RANK = 4

# Longest prefixes first so "left " wins over "l".
_SIDE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("left ", "L"),
    ("right ", "R"),
    ("l-", "L"),
    ("r-", "R"),
    ("l", "L"),
    ("r", "R"),
)


def normalise_token(raw: str) -> str:
    """Collapse whitespace and casefold a raw key name: ``" LShift "`` → ``"lshift"``."""
    return " ".join(raw.split()).casefold()


def split_side(token: str) -> tuple[str | None, str]:
    """Split a raw key into ``(side, base)`` where side is ``"L"``, ``"R"`` or ``None``.

    The side prefix is only stripped when the remainder is a known modifier
    name, so ``lalt`` → ``("L", "alt")`` but ``lever`` → ``(None, "lever")``.
    The returned base is normalised (casefolded).
    """
    normalised = normalise_token(token)
    for prefix, side in _SIDE_PREFIXES:
        if normalised.startswith(prefix):
            remainder = normalised[len(prefix) :].strip()
            if remainder in _KEY_RANK:
                return side, remainder
    return None, normalised


def modifier_sort_key(token: str) -> tuple[int, str, str, str]:
    """Deterministic sort key for a raw modifier key name.

    Order is Ctrl < Alt < Shift < Win < everything else alphabetically, on the
    side-stripped casefolded name. Ties break on the casefolded token and then
    the raw token, so the result never depends on the process hash seed.
    """
    _side, base = split_side(token)
    return (_KEY_RANK.get(base, _OTHER_RANK), base, normalise_token(token), token)


def ordered_keys(keys: Iterable[str]) -> tuple[str, ...]:
    """Return the keys in the built-in rank order (see ``modifier_sort_key``)."""
    return tuple(sorted(keys, key=modifier_sort_key))


# ── Modifier ───────────────────────────────────────────────────────────


@dataclass
class Modifier:
    """An alternative binding active while ``modifiers`` are held.

    ``kind`` and ``source`` are bookkeeping for the application. They take no
    part in equality or ``repr``, so two modifiers with the same key set still
    compare equal and dedup the same way they always have.
    """

    modifiers: set[str]
    command: str
    kind: ModifierKind = field(default=ModifierKind.KEY, compare=False, repr=False)
    source: str | None = field(default=None, compare=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.modifiers, set):
            raise ValueError("Modifiers must be a set")

        if not isinstance(self.command, str):
            raise ValueError("A modifier command must be a string")

        if not isinstance(self.kind, ModifierKind):
            try:
                self.kind = ModifierKind(self.kind)
            except ValueError as err:
                raise ValueError(
                    f"Modifier kind must be a ModifierKind, got {self.kind!r}"
                ) from err

        if self.source is not None and not isinstance(self.source, str):
            raise ValueError("A modifier source must be a string or None")

    @property
    def sorted_keys(self) -> tuple[str, ...]:
        """The key set in the built-in rank order (Ctrl < Alt < Shift < Win < others)."""
        return ordered_keys(self.modifiers)

    def __str__(self):
        flattened_mods = "+".join(self.sorted_keys)
        return f"{self.command} - {str(flattened_mods)}"
