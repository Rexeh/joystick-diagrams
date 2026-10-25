# Sample DCS World profiles for manual testing

A fake DCS "Saved Games" folder for trying out styles, modifier colours, text fitting and the layout editor.

Regenerate or extend it with:

```
uv run python tests/data/sample_profiles/make_dcs_samples.py
```

## Setup

1. Setup → DCS World plugin → set **DCS Saved Games Directory** to `<repo>/tests/data/sample_profiles/DCS`.
2. Export page → assign templates. Each device is paired with a bundled template that uses a different internal draw.io structure:

| Device in the app | Suggested template | Why |
|---|---|---|
| VKBsim Gladiator NXT R | `VKB Sim/VKB-Sim Gladiator NXT R.svg` | flat draw.io layout; dense small boxes (text fit) |
| VKBsim Gladiator NXT R (alternative) | `Starter Template.svg` | the only bundled template with modifier boxes (Button 1, Axis X) |
| Throttle - HOTAS Warthog | `Thrustmaster/Thrustmaster Warthog - Throttle.svg` | compressed draw.io model |
| VPC Constellation ALPHA-R | `Virpil/Virpil Constellation ALPHA R.svg` | grouped cells; axes and slider |

## Profiles

| Profile | Devices | Purpose |
|---|---|---|
| **F-16C_50** | VKB, Warthog throttle | Main test bed: plain binds, 1- / 2- / 3-key modifier combos, 1–5 modifiers per control, left/right keys, device-button modifiers, modifier-only controls, hats, axes |
| **FA-18C_hornet** | VKB | Same controls, different modifiers (RAlt, LWin). Use it to test "Changes apply to: Only FA-18C_hornet" and per-profile previews |
| **A-10C_2** | VKB, Virpil | No modifiers at all. "Original (unchanged)" must look exactly as before; also Virpil axes and slider |
| **Edge-Cases** | VKB | Text escaping: quotes, `&`, `<>`, pre-escaped `&amp;`, backslashes, accents, token-like text, lower-case and unknown modifier names |
| F-16C_50_easy | VKB | Hidden by default ("Remove Easy Mode Profiles"); untick that plugin setting to see it |

## F-16C_50 · VKBsim Gladiator NXT R: control by control

| Control | Base bind | Modifier binds | Tests |
|---|---|---|---|
| Button 1 | Gun Trigger - First Stage | LShift, LCtrl, LAlt, LCtrl+LShift, LCtrl+LAlt+LShift | 5 modifiers incl. 2- and 3-key combos → overflow on 4-box layouts, auto-add, "+N more" |
| Button 2 | Weapon Release | **R**Shift | right-hand Shift grouped with Shift (same colour) |
| Button 3 | TMS Up | LShift | one modifier |
| Button 4 | DMS Up | LShift, LCtrl | two modifiers |
| Button 5 | CMS Aft | LShift, LCtrl, LAlt | three modifiers |
| Button 6 | Expand FOV | LCtrl+LShift | 2-key combo only (box colour = highest-priority key) |
| Button 7 | Nosewheel Steering | RCtrl+RAlt+RShift | 3-key combo, right-hand keys |
| Button 8 | *(none)* | LShift | modifier-only control (no leading separator) |
| Button 9 | Pinky Switch | JOY_BTN4 | joystick-button modifier → "Buttons on your devices" group |
| Button 10 | Speed Brake - Extend | LShift+JOY_BTN4 | keyboard + device-button combo |
| Button 11 | Zoom In Slow | LWin | Win group |
| Button 12 | very long command | long LShift command | text fit / truncation |
| Buttons 13–20 | TMS / DMS / CMS directions | – | plain binds |
| POV 1 U/D/L/R | Trim | – | plain hat binds |
| POV 1 UR / DR / DL | *(none)* | LShift / LCtrl+LShift / LCtrl+LAlt+LShift | modifier-only hat directions with 1-, 2- and 3-key combos |
| Axis X | Roll | LShift (Zoom View) | axis modifier (Starter Template has `AXIS_X_MODIFIER_1` slots) |
| Axis Y / RZ | Pitch / Rudder | – | plain axes |

The template has no `POV_1_UL` placeholder (it has `POV_1_LL`), so no UL bind is included.

## What to check

- **Original (unchanged)** style with no layout changes: output identical to the current release. (Exception: the old export path mangles backslashes, e.g. `\n` → newline and `\f` → an invalid XML character, and crashes on others like `\p`. The new engine handles them.)
- **Appearance → Modifier keys → Colour by modifier key**: LShift / RShift / lshift share one colour; LCtrl / RCtrl share another; JOY_BTN4 uses the "Buttons on your devices" colour; "BMS DX Shift" appears under keys without a group.
- **Appearance → Style → Showing modifiers → Add them under the main text**: Buttons 1, 4, 5 show coloured lines; Button 1 shrinks text or shows "+N more" in small boxes.
- **Layout**: Auto-add on F-16C_50 adds up to 4 boxes on Button 1 (with 1 overflow) and fewer elsewhere; switch "Preview with" to FA-18C_hornet to see different modifiers on the same boxes; try "Only FA-18C_hornet" changes.
- **Edge-Cases**: no `&amp;amp;`, quotes render, `Same as BUTTON_2` is not replaced, and `TEMPLATE_NAME` inside a command stays literal (new engine).
