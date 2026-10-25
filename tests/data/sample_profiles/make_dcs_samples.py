"""Generate a DCS World "Saved Games" sample folder for manually testing styles,
modifier colours and the layout editor.

Usage:
    uv run python tests/data/sample_profiles/make_dcs_samples.py

Writes ``tests/data/sample_profiles/DCS/Config/Input/<aircraft>/joystick/*.diff.lua``.
Point the DCS World plugin's "DCS Saved Games Directory" at
``tests/data/sample_profiles/DCS``. See README.md next to this file for what each
profile and control is meant to exercise.
"""

from pathlib import Path

OUT_ROOT = Path(__file__).parent / "DCS"

# ── Devices (names chosen to match bundled templates) ──
VKB = "VKBsim Gladiator NXT R {A1B2C3D4-0001-11EE-8001-444553540000}"
WARTHOG_THROTTLE = "Throttle - HOTAS Warthog {A1B2C3D4-0002-11EE-8002-444553540000}"
VIRPIL = "VPC Constellation ALPHA-R {A1B2C3D4-0003-11EE-8003-444553540000}"

# A bind is (dcs_key, command, modifier_keys or None). Axes use JOY_X etc,
# hats JOY_BTN_POV1_U etc. Modifier keys are DCS "reformers".
Bind = tuple[str, str, tuple[str, ...] | None]

F16_VKB: list[Bind] = [
    # Button 1: base + five modifier binds (1-, 2- and 3-key combos) -> overflow on 4-box layouts
    ("JOY_BTN1", "Gun Trigger - First Stage", None),
    ("JOY_BTN1", "Laser Arm", ("LShift",)),
    ("JOY_BTN1", "Master Arm Toggle", ("LCtrl",)),
    ("JOY_BTN1", "Camera Snap View", ("LAlt",)),
    ("JOY_BTN1", "Jettison Stores", ("LShift", "LCtrl")),
    ("JOY_BTN1", "Emergency Jettison", ("LShift", "LCtrl", "LAlt")),
    # Button 2: right-hand Shift should group with Shift (same colour as LShift)
    ("JOY_BTN2", "Weapon Release", None),
    ("JOY_BTN2", "Pickle Hold", ("RShift",)),
    # Buttons 3-5: one, two and three separate single-key modifiers
    ("JOY_BTN3", "Target Management Switch - Up", None),
    ("JOY_BTN3", "Target Designate", ("LShift",)),
    ("JOY_BTN4", "Display Management Switch - Up", None),
    ("JOY_BTN4", "HUD Mode Cycle", ("LShift",)),
    ("JOY_BTN4", "MFD Swap", ("LCtrl",)),
    ("JOY_BTN5", "Countermeasures Management - Aft", None),
    ("JOY_BTN5", "Chaff Release", ("LShift",)),
    ("JOY_BTN5", "Flare Release", ("LCtrl",)),
    ("JOY_BTN5", "Countermeasure Program 1", ("LAlt",)),
    # Button 6: double-key combo only; Button 7: triple-key combo only (right-hand keys)
    ("JOY_BTN6", "Expand FOV", None),
    ("JOY_BTN6", "Reset VR Headset", ("LShift", "LCtrl")),
    ("JOY_BTN7", "Nosewheel Steering", None),
    ("JOY_BTN7", "Air Refuel Door Toggle", ("RCtrl", "RShift", "RAlt")),
    # Button 8: modifier-only (no unmodified bind)
    ("JOY_BTN8", "Radio Comms Menu", ("LShift",)),
    # Button 9: joystick-button modifier; Button 10: keyboard + joystick-button combo
    ("JOY_BTN9", "Pinky Switch", None),
    ("JOY_BTN9", "Autopilot Disengage", ("JOY_BTN4",)),
    ("JOY_BTN10", "Speed Brake - Extend", None),
    ("JOY_BTN10", "Speed Brake - Retract Fully", ("LShift", "JOY_BTN4")),
    # Button 11: Windows key modifier
    ("JOY_BTN11", "Zoom In Slow", None),
    ("JOY_BTN11", "Labels Toggle", ("LWin",)),
    # Button 12: long command name (text fit)
    (
        "JOY_BTN12",
        "Communications Command Switch - Down / Transmit Secure Voice UHF Radio",
        None,
    ),
    (
        "JOY_BTN12",
        "Inter-cockpit Communication / Wingman Formation Request",
        ("LShift",),
    ),
    # Plain binds
    ("JOY_BTN13", "Target Management Switch - Down", None),
    ("JOY_BTN14", "Target Management Switch - Left", None),
    ("JOY_BTN15", "Target Management Switch - Right", None),
    ("JOY_BTN16", "Display Management Switch - Down", None),
    ("JOY_BTN17", "Display Management Switch - Left", None),
    ("JOY_BTN18", "Display Management Switch - Right", None),
    ("JOY_BTN19", "Countermeasures Management - Forward", None),
    ("JOY_BTN20", "Countermeasures Management - Left", None),
    # Hat: trim plain; diagonals carry modifiers
    ("JOY_BTN_POV1_U", "Trim: Nose Down", None),
    ("JOY_BTN_POV1_D", "Trim: Nose Up", None),
    ("JOY_BTN_POV1_L", "Trim: Left Wing Down", None),
    ("JOY_BTN_POV1_R", "Trim: Right Wing Down", None),
    ("JOY_BTN_POV1_UR", "View Up Right", ("LShift",)),
    ("JOY_BTN_POV1_DR", "View Down Right", ("LShift", "LCtrl")),
    ("JOY_BTN_POV1_DL", "View Down Left", ("LShift", "LCtrl", "LAlt")),
    # Axes, one with a modifier (Starter Template has AXIS_X modifier slots)
    ("JOY_X", "Roll", None),
    ("JOY_X", "Zoom View", ("LShift",)),
    ("JOY_Y", "Pitch", None),
    ("JOY_RZ", "Rudder", None),
]

F16_THROTTLE: list[Bind] = [
    ("JOY_BTN1", "Mic Switch - Up (UHF)", None),
    ("JOY_BTN1", "UHF Volume Up", ("LShift",)),
    ("JOY_BTN2", "Mic Switch - Down (VHF)", None),
    ("JOY_BTN2", "VHF Volume Up", ("LShift",)),
    ("JOY_BTN2", "IFF Interrogate", ("LCtrl",)),
    ("JOY_BTN3", "Mic Switch - Forward (IFF Out)", None),
    ("JOY_BTN4", "Mic Switch - Aft (IFF In)", None),
    ("JOY_BTN5", "Speedbrake - Out", None),
    ("JOY_BTN5", "Speedbrake - Hold Out", ("LShift", "LCtrl")),
    ("JOY_BTN6", "Speedbrake - In", None),
    ("JOY_BTN7", "Boat Switch - Forward", None),
    ("JOY_BTN8", "Boat Switch - Aft", None),
    ("JOY_BTN9", "China Hat - Forward", None),
    ("JOY_BTN9", "Expand FOV Toggle", ("LAlt",)),
    ("JOY_BTN10", "China Hat - Aft", None),
    ("JOY_BTN11", "Pinky Switch - Forward", None),
    ("JOY_BTN11", "Cockpit Lights", ("RShift", "RCtrl", "RAlt")),
    ("JOY_BTN12", "Pinky Switch - Aft", None),
    ("JOY_BTN13", "Left Throttle Button", ("LShift",)),
    ("JOY_BTN14", "Engine Operate Left", None),
    ("JOY_BTN15", "Engine Operate Right", None),
    ("JOY_BTN16", "APU Start", None),
    ("JOY_BTN17", "Flaps Up", None),
    ("JOY_BTN18", "Flaps Down", None),
]

HORNET_VKB: list[Bind] = [
    # Same controls as the F-16 but different modifiers, for per-profile layout tests
    ("JOY_BTN1", "Gun Trigger", None),
    ("JOY_BTN1", "Sensor Control - Depress", ("RAlt",)),
    ("JOY_BTN1", "Master Arm", ("LCtrl", "RAlt")),
    ("JOY_BTN2", "Weapon Release", None),
    ("JOY_BTN3", "Sensor Control Switch - Fwd", None),
    ("JOY_BTN3", "Radar Elevation Up", ("RAlt",)),
    ("JOY_BTN4", "Sensor Control Switch - Aft", None),
    ("JOY_BTN4", "Radar Elevation Down", ("RAlt",)),
    ("JOY_BTN5", "Weapon Select - Sidewinder", None),
    ("JOY_BTN6", "Weapon Select - Sparrow", None),
    ("JOY_BTN7", "Undesignate / NWS", None),
    ("JOY_BTN7", "Autopilot Disengage", ("LWin",)),
    ("JOY_BTN8", "Communications Menu", ("LShift",)),
    ("JOY_BTN_POV1_U", "Trim: Nose Down", None),
    ("JOY_BTN_POV1_D", "Trim: Nose Up", None),
    ("JOY_BTN_POV1_L", "Trim: Left Wing Down", None),
    ("JOY_BTN_POV1_R", "Trim: Right Wing Down", None),
    ("JOY_X", "Roll", None),
    ("JOY_Y", "Pitch", None),
    ("JOY_RZ", "Rudder", None),
]

A10_VKB: list[Bind] = [
    # Baseline: no modifiers at all ("Original" must look exactly as before)
    ("JOY_BTN1", "Gun Trigger - Fire", None),
    ("JOY_BTN2", "Weapon Release", None),
    ("JOY_BTN3", "TMS Forward Short", None),
    ("JOY_BTN4", "DMS Forward Short", None),
    ("JOY_BTN5", "China Hat Forward Long", None),
    ("JOY_BTN6", "Master Mode Control", None),
    ("JOY_BTN7", "Nosewheel Steering", None),
    ("JOY_BTN_POV1_U", "Trim: Nose Down", None),
    ("JOY_BTN_POV1_D", "Trim: Nose Up", None),
    ("JOY_BTN_POV1_L", "Trim: Left Wing Down", None),
    ("JOY_BTN_POV1_R", "Trim: Right Wing Down", None),
    ("JOY_X", "Roll", None),
    ("JOY_Y", "Pitch", None),
    ("JOY_RZ", "Rudder", None),
]

A10_VIRPIL: list[Bind] = [
    ("JOY_BTN1", "Gun Trigger - Fire", None),
    ("JOY_BTN2", "Weapon Release", None),
    ("JOY_BTN3", "Coolie Hat Up", None),
    ("JOY_BTN4", "Coolie Hat Down", None),
    ("JOY_BTN5", "Target Management Switch - Up", None),
    ("JOY_BTN6", "Target Management Switch - Down", None),
    ("JOY_X", "Roll", None),
    ("JOY_Y", "Pitch", None),
    ("JOY_Z", "Throttle", None),
    ("JOY_RX", "Zoom", None),
    ("JOY_RY", "Brightness", None),
    ("JOY_SLIDER1", "Throttle Friction", None),
]

EDGE_VKB: list[Bind] = [
    # Text edge cases for escaping. NOTE: the "Original (unchanged)" export path
    # mangles backslashes (\n, \f) or crashes on others; the new engine handles them.
    ("JOY_BTN1", 'Fire "Primary" Weapon & <Guns>', None),
    ("JOY_BTN1", 'Rob\'s "Special" Mode', ("LShift",)),
    ("JOY_BTN2", "Already escaped: a &amp; b", None),
    ("JOY_BTN3", "Same as BUTTON_2 (should not be replaced)", None),
    ("JOY_BTN4", "TEMPLATE_NAME and CURRENT_DATE as text", None),
    ("JOY_BTN5", "Path C:\\new\\folder with backslashes", None),
    ("JOY_BTN6", "Ünïcödé — émojis not used, accents only", None),
    ("JOY_BTN7", "Same command on two buttons", None),
    ("JOY_BTN8", "Same command on two buttons", None),
    ("JOY_BTN9", "Lower-case Star Citizen style key", ("lshift",)),
    ("JOY_BTN10", "Unknown modifier name", ("BMS DX Shift",)),
]

EASY_VKB: list[Bind] = [
    ("JOY_BTN1", "Gun Trigger (easy mode profile, should be hidden by default)", None),
]

PROFILES: dict[str, dict[str, list[Bind]]] = {
    "F-16C_50": {VKB: F16_VKB, WARTHOG_THROTTLE: F16_THROTTLE},
    "FA-18C_hornet": {VKB: HORNET_VKB},
    "A-10C_2": {VKB: A10_VKB, VIRPIL: A10_VIRPIL},
    "Edge-Cases": {VKB: EDGE_VKB},
    "F-16C_50_easy": {VKB: EASY_VKB},
}


# ── Lua writer (mimics DCS's *.diff.lua layout) ──
def lua_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def is_axis(key: str) -> bool:
    return not key.startswith("JOY_BTN")


def build_diff(binds: list[Bind]) -> str:
    key_cmds: dict[str, list[tuple[str, tuple[str, ...] | None]]] = {}
    axis_cmds: dict[str, list[tuple[str, tuple[str, ...] | None]]] = {}
    for key, command, mods in binds:
        target = axis_cmds if is_axis(key) else key_cmds
        target.setdefault(command, []).append((key, mods))

    lines = ["local diff = {"]
    for section, cmds, prefix in (
        ("axisDiffs", axis_cmds, "a"),
        ("keyDiffs", key_cmds, "d"),
    ):
        if not cmds:
            continue
        lines.append(f'\t["{section}"] = {{')
        for number, (command, entries) in enumerate(cmds.items(), start=3001):
            lines.append(f'\t\t["{prefix}{number}pnilu{number}cdnil"] = {{')
            lines.append('\t\t\t["added"] = {')
            for index, (key, mods) in enumerate(entries, start=1):
                lines.append(f"\t\t\t\t[{index}] = {{")
                lines.append(f'\t\t\t\t\t["key"] = {lua_string(key)},')
                if mods:
                    lines.append('\t\t\t\t\t["reformers"] = {')
                    for m_index, mod in enumerate(mods, start=1):
                        lines.append(f"\t\t\t\t\t\t[{m_index}] = {lua_string(mod)},")
                    lines.append("\t\t\t\t\t},")
                lines.append("\t\t\t\t},")
            lines.append("\t\t\t},")
            lines.append(f'\t\t\t["name"] = {lua_string(command)},')
            lines.append("\t\t},")
        lines.append("\t},")
    lines.append("}")
    lines.append("return diff")
    return "\n".join(lines) + "\n"


def main() -> None:
    input_dir = OUT_ROOT / "Config" / "Input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "disabled.lua").write_text(
        'local disabled = {\n\t["devices"] = {\n\t},\n\t["pnp"] = false,\n}\nreturn disabled\n',
        encoding="utf-8",
    )
    for profile, devices in PROFILES.items():
        joystick_dir = input_dir / profile / "joystick"
        joystick_dir.mkdir(parents=True, exist_ok=True)
        for device, binds in devices.items():
            (joystick_dir / f"{device}.diff.lua").write_text(
                build_diff(binds), encoding="utf-8"
            )
    print(f"Wrote DCS sample profiles to {OUT_ROOT}")


if __name__ == "__main__":
    main()
