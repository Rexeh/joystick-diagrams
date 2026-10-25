"""Cross-device input routing primitives.

A route expresses "commands bound to input X on device A should display on
input Y of device B (optionally tagged with a qualifier)". The primitive is
generic; plugins populate it per their own semantics. The Joystick Gremlin
parser is the current producer (via `<remap>` actions on physical buttons
targeting vJoy devices), but the primitive is not vJoy-specific.
"""

from collections.abc import Iterable
from copy import deepcopy
from typing import TYPE_CHECKING, NamedTuple

from joystick_diagrams.conflict_strategy import (
    QUALIFIER_SOURCE_INPUT,
    QUALIFIER_SOURCE_ROUTE,
    AliasConflictStrategy,
    apply_input_conflict,
)
from joystick_diagrams.input.axis import Axis, AxisDirection
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import INPUT_AXIS_KEY, INPUT_BUTTON_KEY
from joystick_diagrams.input.input import Input_
from joystick_diagrams.input.modifier import Modifier

if TYPE_CHECKING:
    from joystick_diagrams.input.profile import Profile_

UNKNOWN_DEVICE_NAME = "Unknown Device"


class RouteKey(NamedTuple):
    """Identifies the input that commands are bound to in external profiles.

    For a Gremlin vJoy remap, this is the vJoy device and button the
    physical control feeds into (e.g. vJoy Device 1 / BUTTON_108).
    """

    device_guid: str
    input_type: str
    input_id: str


class RouteTarget(NamedTuple):
    """Where bound commands should be displayed on the diagram.

    For a Gremlin vJoy remap, this is the physical device and input that
    originated the remap (e.g. K51 / BUTTON_1). Qualifier captures tempo
    short/long or activation conditions.
    """

    device_guid: str
    input_type: str
    input_id: str
    qualifier: str


class _PendingRoute(NamedTuple):
    """A source binding waiting to be placed on one destination input.

    ``modifiers`` is the *source* input's modifier list. It is shared between
    the pending entries of a fan-out and must be deep-copied per destination
    when applied, because ``Input_.add_modifier`` later mutates modifiers in
    place (``existing.command = ...``).
    """

    command: str
    qualifier: str
    qualifier_source: str | None
    modifiers: list[Modifier]


_Destination = tuple[str, str, str]


def union_profile_routes(
    profiles: Iterable["Profile_"],
) -> dict[RouteKey, list[RouteTarget]]:
    """Merge input_routes across a collection of profiles.

    On conflicting RouteKey entries, the first profile encountered wins.
    v1 behaviour; cross-Gremlin-file conflicts are rare in practice.
    """
    merged: dict[RouteKey, list[RouteTarget]] = {}
    for profile in profiles:
        for key, targets in profile.input_routes.items():
            if key in merged:
                continue
            merged[key] = list(targets)
    return merged


def apply_routes(
    profile: "Profile_",
    union_routes: dict[RouteKey, list[RouteTarget]],
    strategy: AliasConflictStrategy,
    device_names: dict[str, str],
) -> None:
    """Apply cross-device input routes to a profile in-place.

    For each route whose source matches an input in `profile`, the input is
    popped off the source device and its command *and modifiers* are placed on
    each listed target. Source devices that become empty are dropped.

    Collisions on the same destination input are resolved via the existing
    conflict strategy (first pending route seeds the primary, subsequent
    routes are applied via `apply_input_conflict` with the route's
    qualifier — e.g. "Short", "Long", "Conditional" — as the loser qualifier.)
    Promoted qualifiers are ``ModifierKind.QUALIFIER`` modifiers with
    ``source="route"`` (or ``"input"`` when the qualifier fell back to the
    source input id). The source's own modifiers keep their kind.
    """
    pending = _collect_pending_routes(profile, union_routes, strategy)

    for destination, items in pending.items():
        _apply_pending_to_destination(
            profile, destination, items, strategy, device_names
        )

    _drop_empty_devices(profile)


def _collect_pending_routes(
    profile: "Profile_",
    union_routes: dict[RouteKey, list[RouteTarget]],
    strategy: AliasConflictStrategy,
) -> dict[_Destination, list[_PendingRoute]]:
    """Pop every routed source input off its device and queue it per destination."""
    pending: dict[_Destination, list[_PendingRoute]] = {}

    for route_key, targets in union_routes.items():
        source_device = profile.devices.get(route_key.device_guid)
        if source_device is None:
            continue
        source_input = source_device.get_input(route_key.input_type, route_key.input_id)
        if source_input is None:
            continue

        source_command = source_input.command
        source_modifiers = source_input.modifiers
        del source_device.inputs[route_key.input_type][route_key.input_id]

        for target in targets:
            dst_tuple = (target.device_guid, target.input_type, target.input_id)
            qualifier, qualifier_source = _resolve_loser_qualifier(
                target.qualifier, route_key.input_id, strategy
            )
            pending.setdefault(dst_tuple, []).append(
                _PendingRoute(
                    source_command, qualifier, qualifier_source, source_modifiers
                )
            )

    return pending


def _apply_pending_to_destination(
    profile: "Profile_",
    destination: _Destination,
    items: list[_PendingRoute],
    strategy: AliasConflictStrategy,
    device_names: dict[str, str],
) -> None:
    """Place the queued source bindings on one destination input."""
    dst_guid, dst_type, dst_id = destination
    control = _make_control(dst_type, dst_id)
    if control is None:
        return

    dst_device = profile.devices.get(dst_guid)
    if dst_device is None:
        dst_device = profile.add_device(
            dst_guid, device_names.get(dst_guid, UNKNOWN_DEVICE_NAME)
        )

    dst_input = dst_device.get_input(dst_type, dst_id)

    if dst_input is None:
        first = items[0]
        dst_device.create_input(control, first.command)
        dst_input = dst_device.get_input(dst_type, dst_id)
        _merge_modifiers_winner_wins(dst_input, first.modifiers)
        remaining = items[1:]
    else:
        remaining = items

    for item in remaining:
        loser = Input_(control, item.command)
        loser.modifiers = _copy_modifiers(item.modifiers)
        apply_input_conflict(
            winner=dst_input,
            loser=loser,
            loser_qualifier=item.qualifier,
            strategy=strategy,
            qualifier_source=item.qualifier_source,
        )


def _copy_modifiers(modifiers: list[Modifier]) -> list[Modifier]:
    """Deep-copy a modifier list so each destination owns independent objects."""
    return [deepcopy(modifier) for modifier in modifiers]


def _merge_modifiers_winner_wins(winner: Input_, modifiers: list[Modifier]) -> None:
    """Append copies of `modifiers` to `winner`, skipping key-set collisions."""
    for modifier in modifiers:
        if winner._check_existing_modifier(modifier.modifiers) is None:
            winner.modifiers.append(deepcopy(modifier))


def _resolve_loser_qualifier(
    target_qualifier: str, source_input_id: str, strategy: AliasConflictStrategy
) -> tuple[str, str | None]:
    """Pick the qualifier passed to apply_input_conflict for a route.

    Returns ``(qualifier, qualifier_source)``. Basic containers have no
    qualifier. Under CONCATENATE we leave it empty (bare join, no `[…]`
    prefix). Under MODIFIER we fall back to the source input's identifier so
    the promoted modifier isn't keyed by the empty string; the source is then
    ``"input"`` rather than ``"route"``.
    """
    if target_qualifier:
        return target_qualifier, QUALIFIER_SOURCE_ROUTE
    if strategy == AliasConflictStrategy.MODIFIER:
        return source_input_id, QUALIFIER_SOURCE_INPUT
    return "", None


def _make_control(input_type: str, input_id: str) -> Axis | Button | None:
    """Reconstruct a Button/Axis control object from (input_type, input_id)."""
    if input_type == INPUT_BUTTON_KEY:
        return _button_from_id(input_id)
    if input_type == INPUT_AXIS_KEY:
        return _axis_from_id(input_id)
    return None


def _button_from_id(input_id: str) -> Button | None:
    if not input_id.startswith("BUTTON_"):
        return None
    try:
        return Button(int(input_id.removeprefix("BUTTON_")))
    except ValueError:
        return None


def _axis_from_id(input_id: str) -> Axis | None:
    if not input_id.startswith("AXIS_"):
        return None
    try:
        return Axis(AxisDirection[input_id.removeprefix("AXIS_")])
    except KeyError:
        return None


def _drop_empty_devices(profile: "Profile_") -> None:
    for guid in list(profile.devices.keys()):
        device = profile.devices[guid]
        if all(len(inputs) == 0 for inputs in device.inputs.values()):
            del profile.devices[guid]
