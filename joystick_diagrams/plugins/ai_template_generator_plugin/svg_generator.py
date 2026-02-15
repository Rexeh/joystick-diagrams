"""SVG Template Generator for Joystick Diagrams.

Generates draw.io compatible SVG templates from AI analysis results.
The generated SVGs contain mxCell placeholders (BUTTON_X, AXIS_X, POV_X_Y etc.)
that are compatible with the Joystick Diagrams template system.
"""

import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from joystick_diagrams.plugins.ai_template_generator_plugin.ai_analyzer import (
    AnalysisResult,
    DetectedControl,
)

_logger = logging.getLogger(__name__)

# SVG canvas dimensions
CANVAS_WIDTH = 1169
CANVAS_HEIGHT = 827

# Control box dimensions
BOX_WIDTH = 160
BOX_HEIGHT = 35
BOX_SPACING = 8

# Modifier count per control
MODIFIERS_PER_CONTROL = 2

# Style constants for draw.io mxCell elements
STYLE_BUTTON = "rounded=1;whiteSpace=wrap;html=1;strokeColor=#6c8ebf;strokeWidth=2;align=left;fillColor=#dae8fc;"
STYLE_AXIS = "rounded=1;whiteSpace=wrap;html=1;strokeColor=#82b366;strokeWidth=2;align=left;fillColor=#d5e8d4;"
STYLE_HAT = "rounded=1;whiteSpace=wrap;html=1;strokeColor=#d6b656;strokeWidth=2;align=left;fillColor=#fff2cc;"
STYLE_SLIDER = "rounded=1;whiteSpace=wrap;html=1;strokeColor=#9673a6;strokeWidth=2;align=left;fillColor=#e1d5e7;"
STYLE_LABEL = "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=10;fontStyle=1"
STYLE_HEADER = "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=16;fontStyle=5"
STYLE_META = "rounded=1;whiteSpace=wrap;html=1;strokeColor=#CC0000;strokeWidth=2;align=left;"
STYLE_IMAGE = "shape=image;verticalLabelPosition=bottom;labelBackgroundColor=default;verticalAlign=top;imageAspect=0;opacity=80;"

# Hat switch directions
HAT_DIRECTIONS = ["U", "D", "L", "R", "UR", "UL", "DR", "DL"]


def _get_style(control: DetectedControl) -> str:
    """Get the draw.io style string for a control type."""
    styles = {
        "button": STYLE_BUTTON,
        "axis": STYLE_AXIS,
        "hat": STYLE_HAT,
        "slider": STYLE_SLIDER,
    }
    return styles.get(control.control_type, STYLE_BUTTON)


def _axis_name_for_id(axis_id: int) -> str:
    """Map axis ID to standard axis name."""
    axis_names = {
        1: "AXIS_X",
        2: "AXIS_Y",
        3: "AXIS_Z",
        4: "AXIS_RX",
        5: "AXIS_RY",
        6: "AXIS_RZ",
    }
    return axis_names.get(axis_id, f"AXIS_SLIDER_{axis_id - 6}")


@dataclass
class CellSpec:
    """Specification for a draw.io mxCell element."""

    cell_id: str
    value: str
    style: str
    x: int
    y: int
    w: int
    h: int


def _generate_mxcell(spec: CellSpec) -> str:
    """Generate a single mxCell XML element."""
    escaped_value = escape(spec.value)
    return (
        f'        <mxCell id="{spec.cell_id}" value="{escaped_value}" '
        f'style="{spec.style}" parent="1" vertex="1">\n'
        f'          <mxGeometry x="{spec.x}" y="{spec.y}" width="{spec.w}" height="{spec.h}" as="geometry" />\n'
        f"        </mxCell>\n"
    )


def _generate_control_cells(controls: list[DetectedControl]) -> str:
    """Generate mxCell elements for all controls."""
    cells = ""
    cell_counter = 100

    # Group controls by type
    buttons = [c for c in controls if c.control_type == "button"]
    axes = [c for c in controls if c.control_type == "axis"]
    hats = [c for c in controls if c.control_type == "hat"]
    sliders = [c for c in controls if c.control_type == "slider"]

    # Generate button cells
    for btn in buttons:
        placeholder = f"BUTTON_{btn.control_id}"
        x = int(btn.x * CANVAS_WIDTH)
        y = int(btn.y * CANVAS_HEIGHT)

        # Label
        cells += _generate_mxcell(CellSpec(
            f"label_{cell_counter}", escape(btn.label), STYLE_LABEL, x, y - 15, BOX_WIDTH, 15,
        ))
        cell_counter += 1

        # Button placeholder
        cells += _generate_mxcell(CellSpec(
            f"ctrl_{cell_counter}", placeholder, STYLE_BUTTON, x, y, BOX_WIDTH, BOX_HEIGHT,
        ))
        cell_counter += 1

        # Modifier placeholders
        mod_y = y + BOX_HEIGHT + BOX_SPACING
        cells += _generate_mxcell(CellSpec(
            f"mod_{cell_counter}", f"{placeholder}_MODIFIERS", STYLE_BUTTON, x, mod_y, BOX_WIDTH, BOX_HEIGHT,
        ))
        cell_counter += 1

        for mod_num in range(1, MODIFIERS_PER_CONTROL + 1):
            offset_y = y + (BOX_HEIGHT + BOX_SPACING) * (mod_num + 1)
            cells += _generate_mxcell(CellSpec(
                f"modk_{cell_counter}", f"{placeholder}_Modifier_{mod_num}_Key",
                STYLE_BUTTON, x, offset_y, BOX_WIDTH // 2, BOX_HEIGHT,
            ))
            cell_counter += 1

            cells += _generate_mxcell(CellSpec(
                f"moda_{cell_counter}", f"{placeholder}_Modifier_{mod_num}_Action",
                STYLE_BUTTON, x + BOX_WIDTH // 2, offset_y, BOX_WIDTH // 2, BOX_HEIGHT,
            ))
            cell_counter += 1

    # Generate axis cells
    for ax in axes:
        placeholder = _axis_name_for_id(ax.control_id)
        x = int(ax.x * CANVAS_WIDTH)
        y = int(ax.y * CANVAS_HEIGHT)

        cells += _generate_mxcell(CellSpec(
            f"label_{cell_counter}", escape(ax.label), STYLE_LABEL, x, y - 15, BOX_WIDTH, 15,
        ))
        cell_counter += 1

        cells += _generate_mxcell(CellSpec(
            f"ctrl_{cell_counter}", placeholder, STYLE_AXIS, x, y, BOX_WIDTH, BOX_HEIGHT,
        ))
        cell_counter += 1

    # Generate slider cells (as AXIS_SLIDER_X)
    for sl in sliders:
        placeholder = f"AXIS_SLIDER_{sl.control_id}"
        x = int(sl.x * CANVAS_WIDTH)
        y = int(sl.y * CANVAS_HEIGHT)

        cells += _generate_mxcell(CellSpec(
            f"label_{cell_counter}", escape(sl.label), STYLE_LABEL, x, y - 15, BOX_WIDTH, 15,
        ))
        cell_counter += 1

        cells += _generate_mxcell(CellSpec(
            f"ctrl_{cell_counter}", placeholder, STYLE_SLIDER, x, y, BOX_WIDTH, BOX_HEIGHT,
        ))
        cell_counter += 1

    # Generate hat cells (8 directions per hat)
    for hat in hats:
        base_x = int(hat.x * CANVAS_WIDTH)
        base_y = int(hat.y * CANVAS_HEIGHT)

        cells += _generate_mxcell(CellSpec(
            f"label_{cell_counter}", escape(hat.label), STYLE_LABEL, base_x, base_y - 15, BOX_WIDTH, 15,
        ))
        cell_counter += 1

        for i, direction in enumerate(HAT_DIRECTIONS):
            placeholder = f"POV_{hat.control_id}_{direction}"
            dir_y = base_y + i * (BOX_HEIGHT + BOX_SPACING)

            cells += _generate_mxcell(CellSpec(
                f"ctrl_{cell_counter}", placeholder, STYLE_HAT, base_x, dir_y, BOX_WIDTH, BOX_HEIGHT,
            ))
            cell_counter += 1

    return cells


def _generate_image_cell(image_path: Path) -> str:
    """Generate mxCell for the background controller image."""
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    suffix = image_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    media_type = media_types.get(suffix, "image/png")

    style = f"{STYLE_IMAGE}image=data:{media_type},{image_data};"

    return (
        f'        <mxCell id="bg_image" value="" '
        f'style="{style}" parent="1" vertex="1">\n'
        f'          <mxGeometry x="0" y="0" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" as="geometry" />\n'
        f"        </mxCell>\n"
    )


def generate_template(analysis: AnalysisResult, image_path: Path, embed_image: bool = True) -> str:
    """Generate a draw.io compatible SVG template from analysis results.

    Args:
        analysis: The AI analysis result containing detected controls
        image_path: Path to the original controller image
        embed_image: Whether to embed the image as background (default True)

    Returns:
        SVG template string in draw.io format
    """
    _logger.info(
        f"Generating template for {analysis.device_name} "
        f"with {len(analysis.controls)} controls"
    )

    # Build mxGraphModel content
    mx_cells = ""

    # Background image
    if embed_image and image_path.exists():
        mx_cells += _generate_image_cell(image_path)

    # Control placeholder cells
    mx_cells += _generate_control_cells(analysis.controls)

    # Template name and date placeholders
    mx_cells += _generate_mxcell(CellSpec(
        "meta_name", "TEMPLATE_NAME", STYLE_META, 10, CANVAS_HEIGHT - 60, 200, 25,
    ))
    mx_cells += _generate_mxcell(CellSpec(
        "meta_date", "CURRENT_DATE", STYLE_META, 10, CANVAS_HEIGHT - 30, 200, 25,
    ))

    # Build the mxGraphModel XML (stored in SVG content attribute)
    mx_graph_model = (
        '<mxfile host="ai-template-generator" modified="2024-01-01T00:00:00.000Z" '
        'agent="AI Template Generator" version="1.0.0" type="device">\n'
        f'  <diagram id="ai-generated" name="{escape(analysis.device_name)}">\n'
        f'    <mxGraphModel dx="{CANVAS_WIDTH}" dy="{CANVAS_HEIGHT}" grid="1" '
        f'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" '
        f'page="1" pageScale="1" pageWidth="{CANVAS_WIDTH}" pageHeight="{CANVAS_HEIGHT}" '
        f'math="0" shadow="0">\n'
        f"      <root>\n"
        f'        <mxCell id="0" />\n'
        f'        <mxCell id="1" parent="0" />\n'
        f"{mx_cells}"
        f"      </root>\n"
        f"    </mxGraphModel>\n"
        f"  </diagram>\n"
        f"</mxfile>\n"
    )

    # Escape for SVG content attribute
    content_escaped = escape(mx_graph_model).replace("\n", "&#10;")

    # Build rendered SVG elements
    svg_elements = _generate_svg_rendered_elements(analysis.controls, image_path, embed_image)

    # Final SVG
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!-- Do not edit this file with editors other than draw.io -->\n"
        '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
        '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'version="1.1" width="{CANVAS_WIDTH}px" height="{CANVAS_HEIGHT}px" '
        f'viewBox="-0.5 -0.5 {CANVAS_WIDTH} {CANVAS_HEIGHT}" '
        f'content="{content_escaped}">'
        f"<defs/>\n<g>\n"
        f"{svg_elements}"
        f"</g>\n"
        f"</svg>\n"
    )

    return svg


def _generate_svg_rendered_elements(
    controls: list[DetectedControl],
    image_path: Path,
    embed_image: bool,
) -> str:
    """Generate the visible SVG elements that render in browsers."""
    elements = ""

    # Background image
    if embed_image and image_path.exists():
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        suffix = image_path.suffix.lower()
        media_type = "image/png" if suffix == ".png" else "image/jpeg"
        elements += (
            f'<image x="0" y="0" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" '
            f'xlink:href="data:{media_type};base64,{image_data}" '
            f'opacity="0.8" preserveAspectRatio="xMidYMid meet" />\n'
        )

    # Render control boxes
    buttons = [c for c in controls if c.control_type == "button"]
    axes = [c for c in controls if c.control_type == "axis"]
    hats = [c for c in controls if c.control_type == "hat"]
    sliders = [c for c in controls if c.control_type == "slider"]

    for btn in buttons:
        placeholder = f"BUTTON_{btn.control_id}"
        x = int(btn.x * CANVAS_WIDTH)
        y = int(btn.y * CANVAS_HEIGHT)
        elements += _render_box(CellSpec("", placeholder, "", x, y, BOX_WIDTH, BOX_HEIGHT), "#dae8fc", "#6c8ebf")

    for ax in axes:
        placeholder = _axis_name_for_id(ax.control_id)
        x = int(ax.x * CANVAS_WIDTH)
        y = int(ax.y * CANVAS_HEIGHT)
        elements += _render_box(CellSpec("", placeholder, "", x, y, BOX_WIDTH, BOX_HEIGHT), "#d5e8d4", "#82b366")

    for sl in sliders:
        placeholder = f"AXIS_SLIDER_{sl.control_id}"
        x = int(sl.x * CANVAS_WIDTH)
        y = int(sl.y * CANVAS_HEIGHT)
        elements += _render_box(CellSpec("", placeholder, "", x, y, BOX_WIDTH, BOX_HEIGHT), "#e1d5e7", "#9673a6")

    for hat in hats:
        base_x = int(hat.x * CANVAS_WIDTH)
        base_y = int(hat.y * CANVAS_HEIGHT)
        for i, direction in enumerate(HAT_DIRECTIONS):
            placeholder = f"POV_{hat.control_id}_{direction}"
            dir_y = base_y + i * (BOX_HEIGHT + BOX_SPACING)
            elements += _render_box(CellSpec("", placeholder, "", base_x, dir_y, BOX_WIDTH, BOX_HEIGHT), "#fff2cc", "#d6b656")

    # TEMPLATE_NAME and CURRENT_DATE
    elements += _render_box(CellSpec("", "TEMPLATE_NAME", "", 10, CANVAS_HEIGHT - 60, 200, 25), "#ffffff", "#cc0000")
    elements += _render_box(CellSpec("", "CURRENT_DATE", "", 10, CANVAS_HEIGHT - 30, 200, 25), "#ffffff", "#cc0000")

    return elements


def _render_box(spec: CellSpec, fill: str, stroke: str) -> str:
    """Render a single control box as SVG rect + text."""
    x, y, w, h = spec.x, spec.y, spec.w, spec.h
    text = spec.value
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" ry="6" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="2" pointer-events="all"/>\n'
        f'<g transform="translate(-0.5 -0.5)"><switch>'
        f'<foreignObject pointer-events="none" width="100%" height="100%" '
        f'requiredFeatures="http://www.w3.org/TR/SVG11/feature#Extensibility" '
        f'style="overflow: visible; text-align: left;">'
        f'<div xmlns="http://www.w3.org/1999/xhtml" style="display: flex; '
        f"align-items: unsafe center; justify-content: unsafe flex-start; "
        f"width: {w - 2}px; height: 1px; padding-top: {y + h // 2}px; "
        f'margin-left: {x + 2}px;">'
        f'<div style="box-sizing: border-box; font-size: 0px; text-align: left;">'
        f'<div style="display: inline-block; font-size: 12px; font-family: Helvetica; '
        f"color: rgb(0, 0, 0); line-height: 1.2; pointer-events: all; "
        f'white-space: normal; overflow-wrap: normal;">'
        f"{escape(text)}</div></div></div></foreignObject>"
        f'<text x="{x + 2}" y="{y + h // 2 + 4}" fill="rgb(0, 0, 0)" '
        f'font-family="Helvetica" font-size="12px">{escape(text)}</text>'
        f"</switch></g>\n"
    )


def save_template(svg_content: str, device_name: str, output_dir: Path) -> Path:
    """Save generated SVG template to disk.

    Args:
        svg_content: The SVG template string
        device_name: Name of the device (used for filename)
        output_dir: Directory to save the template

    Returns:
        Path to the saved template file
    """
    # Sanitize filename
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in device_name)
    file_name = f"{safe_name}.svg"
    output_path = output_dir / file_name

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    _logger.info(f"Template saved to: {output_path}")
    return output_path
