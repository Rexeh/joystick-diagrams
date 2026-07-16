"""Strategies for resolving binding conflicts during profile inheritance and device alias merges.

When two sides of a merge both have a primary binding on the same input key,
the strategy decides what happens to the losing side's binding:

- KEEP_EXISTING: winner's primary stays, loser's primary dropped (inheritance only).
- MODIFIER: loser's primary is promoted to a Modifier on the winner's input.
- CONCATENATE: winner's primary rewritten to "winner | loser".

In all cases, loser's own existing modifiers merge into winner's modifier list
via key-set dedup, with winner winning on key-set collisions.
"""

import logging
from copy import deepcopy
from enum import Enum

from joystick_diagrams.db import db_settings
from joystick_diagrams.input.input import Input_
from joystick_diagrams.input.modifier import Modifier

_logger = logging.getLogger(__name__)

ALIAS_CONFLICT_STRATEGY_KEY = "alias_conflict_strategy"
INHERITANCE_CONFLICT_STRATEGY_KEY = "inheritance_conflict_strategy"

CONCATENATE_SEPARATOR = " | "


class AliasConflictStrategy(str, Enum):
    MODIFIER = "MODIFIER"
    CONCATENATE = "CONCATENATE"


class InheritanceConflictStrategy(str, Enum):
    KEEP_EXISTING = "KEEP_EXISTING"
    MODIFIER = "MODIFIER"
    CONCATENATE = "CONCATENATE"


DEFAULT_ALIAS_STRATEGY = AliasConflictStrategy.CONCATENATE
DEFAULT_INHERITANCE_STRATEGY = InheritanceConflictStrategy.KEEP_EXISTING


def get_alias_strategy() -> AliasConflictStrategy:
    raw = db_settings.get_setting(ALIAS_CONFLICT_STRATEGY_KEY)
    if raw is None:
        return DEFAULT_ALIAS_STRATEGY
    try:
        return AliasConflictStrategy(raw)
    except ValueError:
        _logger.warning(
            f"Invalid alias conflict strategy in settings: {raw!r}, using default"
        )
        return DEFAULT_ALIAS_STRATEGY


def get_inheritance_strategy() -> InheritanceConflictStrategy:
    raw = db_settings.get_setting(INHERITANCE_CONFLICT_STRATEGY_KEY)
    if raw is None:
        return DEFAULT_INHERITANCE_STRATEGY
    try:
        return InheritanceConflictStrategy(raw)
    except ValueError:
        _logger.warning(
            f"Invalid inheritance conflict strategy in settings: {raw!r}, using default"
        )
        return DEFAULT_INHERITANCE_STRATEGY


def apply_input_conflict(
    winner: Input_,
    loser: Input_,
    loser_qualifier: str,
    strategy: AliasConflictStrategy | InheritanceConflictStrategy,
) -> None:
    """Merge the losing input into the winning input in-place per `strategy`.

    Preserves winner's modifier ordering. Loser's modifiers are appended via
    key-set dedup; winner wins on collision (loser's colliding modifier skipped).

    For MODIFIER strategy, the promoted modifier uses `{loser_qualifier}` as its
    modifiers set. If that key-set already exists on the winner, the promotion
    is skipped (loser's primary is still expressed as the existing modifier).
    """
    strategy_value = strategy.value if isinstance(strategy, Enum) else str(strategy)

    if strategy_value == "CONCATENATE":
        loser_segment = (
            f"[{loser_qualifier}] {loser.command}" if loser_qualifier else loser.command
        )
        winner.command = f"{winner.command}{CONCATENATE_SEPARATOR}{loser_segment}"
    elif strategy_value == "MODIFIER":
        promoted_keys = {loser_qualifier}
        if winner._check_existing_modifier(promoted_keys) is None:
            winner.modifiers.append(Modifier(promoted_keys, loser.command))

    for modifier in loser.modifiers:
        if winner._check_existing_modifier(modifier.modifiers) is None:
            winner.modifiers.append(deepcopy(modifier))
