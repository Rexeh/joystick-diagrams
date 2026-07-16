"""Cross-device input routing primitives.

A route expresses "commands bound to input X on device A should display on
input Y of device B (optionally tagged with a qualifier)". The primitive is
generic; plugins populate it per their own semantics. The Joystick Gremlin
parser is the current producer (via `<remap>` actions on physical buttons
targeting vJoy devices), but the primitive is not vJoy-specific.
"""

from collections.abc import Iterable
from typing import TYPE_CHECKING, NamedTuple

from joystick_diagrams.conflict_strategy import (
    AliasConflictStrategy,
    apply_input_conflict,
)
from joystick_diagrams.input.axis import Axis, AxisDirection
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import INPUT_AXIS_KEY, INPUT_BUTTON_KEY
from joystick_diagrams.input.input import Input_

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
    popped off the source device and its command is placed on each listed
    target. Source devices that become empty are dropped.

    Collisions on the same destination input are resolved via the existing
    conflict strategy (first pending route seeds the primary, subsequent
    routes are applied via `apply_input_conflict` with the route's
    qualifier — e.g. "Short", "Long", "Conditional" — as the loser qualifier.)
    """
    pending: dict[tuple[str, str, str], list[tuple[str, str]]] = {}

    for route_key, targets in union_routes.items():
        source_device = profile.devices.get(route_key.device_guid)
        if source_device is None:
            continue
        source_input = source_device.get_input(route_key.input_type, route_key.input_id)
        if source_input is None:
            continue

        source_command = source_input.command
        del source_device.inputs[route_key.input_type][route_key.input_id]

        for target in targets:
            dst_tuple = (target.device_guid, target.input_type, target.input_id)
            effective_qualifier = _resolve_loser_qualifier(
                target.qualifier, route_key.input_id, strategy
            )
            pending.setdefault(dst_tuple, []).append(
                (source_command, effective_qualifier)
            )

    for (dst_guid, dst_type, dst_id), items in pending.items():
        control = _make_control(dst_type, dst_id)
        if control is None:
            continue

        dst_device = profile.devices.get(dst_guid)
        if dst_device is None:
            dst_device = profile.add_device(
                dst_guid, device_names.get(dst_guid, UNKNOWN_DEVICE_NAME)
            )

        dst_input = dst_device.get_input(dst_type, dst_id)

        if dst_input is None:
            first_cmd, _first_qual = items[0]
            dst_device.create_input(control, first_cmd)
            dst_input = dst_device.get_input(dst_type, dst_id)
            remaining = items[1:]
        else:
            remaining = items

        for cmd, qualifier in remaining:
            loser = Input_(control, cmd)
            apply_input_conflict(
                winner=dst_input,
                loser=loser,
                loser_qualifier=qualifier,
                strategy=strategy,
            )

    _drop_empty_devices(profile)


def _resolve_loser_qualifier(
    target_qualifier: str, source_input_id: str, strategy: AliasConflictStrategy
) -> str:
    """Pick the qualifier string passed to apply_input_conflict for a route.

    Basic containers have no qualifier. Under CONCATENATE we leave it empty
    (bare join, no `[…]` prefix). Under MODIFIER we fall back to the source
    input's identifier so the promoted modifier isn't keyed by the empty
    string.
    """
    if target_qualifier:
        return target_qualifier
    if strategy == AliasConflictStrategy.MODIFIER:
        return source_input_id
    return ""


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
