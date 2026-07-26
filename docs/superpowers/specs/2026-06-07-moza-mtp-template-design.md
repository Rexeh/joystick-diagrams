# MOZA MTP Throttle Panel template — design

**Date:** 2026-06-07
**Status:** Approved (proof-of-concept for a repeatable MOZA template workflow)

## Goal

Produce a Joystick Diagrams template for the MOZA MTP Throttle Panel by:

1. Reading control numbers from the MOZA reference diagram.
2. Translating those numbers into Joystick Diagrams tokens (`BUTTON_20`, `AXIS_RX`, ...).
3. Overlaying token labels onto the MOZA product photo, embedded in a draw.io-editable SVG.

MTP is the first device; if the workflow proves out, the same process is repeated for the
other MOZA devices (MH-16, MTQ, MA3X, MRP, MTLP, AY210+MFY, AB6/MHG).

## Source materials

- **Reference diagram (control numbering):**
  `.local/templates/moza/MOZA Flight Devices-...zip` → `MOZA Flight Devices/MTP/MTP.png`
  (2400×1874). Flat schematic: panel on the left with numbered circles for buttons; throttle
  grip drawn separately on the right with axis labels (X, Y, RX, RY, RZ = `32767`) and its own
  numbered buttons.
- **Target photo (template background):**
  `.../MOZA Flight/MTP Throttle Panel/Web Page/pc/MTP-Page-4.png` (4536×1843; panel occupies
  the left ~40%, remainder is white). Angled product shot with the throttle grip overlapping
  and partially obscuring the centre of the panel.
- **Example template (target format):** `templates/VKB Sim/VKB-Sim Gladiator NXT L.svg`.

The reference and the target are *different renderings* — coordinates do not transfer between
them. The reference is used only to establish control identity (number ↔ physical control);
labels are then placed by locating each control on the target photo.

## How templates work (context)

- A template is a draw.io SVG. Text labels contain placeholder tokens.
- `Template` ([joystick_diagrams/template.py](../../../joystick_diagrams/template.py)) regex-scans
  the raw SVG text for tokens:
  - `BUTTON_\d+` (case-insensitive)
  - `AXIS_[a-zA-Z]+_?\d?` (e.g. `AXIS_X`, `AXIS_RX`)
  - `POV_\d+_[URDL]+`
  - modifiers, `TEMPLATE_NAME`, `CURRENT_DATE`
- At export ([joystick_diagrams/export.py](../../../joystick_diagrams/export.py)), each token is
  regex-replaced with the user's bound command; unused tokens are blanked.
- Therefore any SVG containing the correct token *text* works with the app — the draw.io
  `content="..."` attribute only matters for editability in diagrams.net.

## Token mapping

- **Buttons:** reference circle `N` → `BUTTON_N` (1:1).
- **Axes:** `X→AXIS_X`, `Y→AXIS_Y`, `RX→AXIS_RX`, `RY→AXIS_RY`, `RZ→AXIS_RZ`.
- **Hat/POV** (if present on the panel) → `POV_1_U` / `_D` / `_L` / `_R`.
- **Title labels:** `TEMPLATE_NAME` + `CURRENT_DATE`, matching existing templates.

## Output (two files)

Under `templates/MOZA/`:

1. **`MOZA MTP Throttle Panel.drawio`** — plain mxGraphModel XML. Editing artifact; opens fully
   editable in diagrams.net so positions can be nudged.
2. **`MOZA MTP Throttle Panel.svg`** — rendered SVG with the cropped panel photo embedded as
   base64 and positioned `<text>` token labels. Works immediately with the export pipeline.

Refinement workflow: open the `.drawio`, reposition labels in diagrams.net, re-export the SVG
over file #2.

Rejected alternative: a single self-contained `.drawio.svg` (existing-template format) requires
replicating draw.io's deflate+base64 `content` encoding; if slightly off, draw.io editability is
lost. The two-file route is lower-risk.

## Build sequence

1. **Reference verification & mapping (feasibility gate).** Crop and upscale MTP.png region by
   region, read every number and axis label, and produce a mapping table
   (number ↔ physical control ↔ token). If numbers cannot be read reliably, stop and report.
2. **Prepare background.** Crop MTP-Page-4.png to the panel region; embed as base64.
3. **Place labels.** One token label per mapped control, at best-guess coordinates over the
   photo. Controls occluded by the grip get a label parked at the grip edge for the user to
   reposition.
4. **Emit** `.drawio` + `.svg`.
5. **Sanity-check.** Load the `.svg` via `Template(...)`; confirm parsed `BUTTON`/`AXIS` counts
   match the mapping table.

## Scope

In: MOZA MTP only. Out: all other MOZA devices (validate workflow on MTP first).

## Risks

- Some controls are occluded by the grip in the chosen photo (accepted by user).
- Reference-number legibility — mitigated by upscaling; explicit gate at step 1.
- 1:1 number→button-index assumption — matches the brief; verified at step 5 against counts.
- Label placement is approximate by design; final positioning is done by the user in
  diagrams.net.
