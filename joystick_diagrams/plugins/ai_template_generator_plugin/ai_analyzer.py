"""AI Vision backend for analyzing controller images.

Supports both Anthropic Claude and OpenAI GPT-4 Vision APIs.
"""

import base64
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from joystick_diagrams.plugins.ai_template_generator_plugin.prompts import (
    ANALYSIS_PROMPT,
    SYSTEM_PROMPT,
)

_logger = logging.getLogger(__name__)


@dataclass
class DetectedControl:
    """A single detected control on a device."""

    control_type: str  # "button", "axis", "hat", "slider"
    control_id: int
    label: str
    x: float  # 0.0-1.0 relative position
    y: float  # 0.0-1.0 relative position


@dataclass
class AnalysisResult:
    """Result of AI image analysis."""

    device_name: str
    device_type: str
    controls: list[DetectedControl] = field(default_factory=list)


def _load_image_as_base64(image_path: Path) -> str:
    """Load an image file and return base64 encoded string."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _get_media_type(image_path: Path) -> str:
    """Get the media type for an image file."""
    suffix = image_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    return media_types.get(suffix, "image/png")


def _parse_response(response_text: str) -> AnalysisResult:
    """Parse the AI response JSON into an AnalysisResult."""
    # Strip markdown code fences if present
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [line for line in lines[1:] if line.strip() != "```"]
        text = "\n".join(lines)

    data = json.loads(text)

    controls = []
    for ctrl in data.get("controls", []):
        controls.append(
            DetectedControl(
                control_type=ctrl["type"],
                control_id=ctrl["id"],
                label=ctrl.get("label", f"{ctrl['type']}_{ctrl['id']}"),
                x=float(ctrl["x"]),
                y=float(ctrl["y"]),
            )
        )

    return AnalysisResult(
        device_name=data.get("device_name", "Unknown Device"),
        device_type=data.get("device_type", "other"),
        controls=controls,
    )


def analyze_with_claude(image_path: Path) -> AnalysisResult:
    """Analyze a controller image using Anthropic Claude Vision API."""
    try:
        import anthropic  # noqa: PLC0415
    except ImportError as e:
        raise ImportError(
            "anthropic package is required. Install with: pip install anthropic"
        ) from e

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)

    image_data = _load_image_as_base64(image_path)
    media_type = _get_media_type(image_path)

    _logger.info(f"Analyzing image with Claude: {image_path.name}")

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": ANALYSIS_PROMPT,
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text
    _logger.debug(f"Claude response: {response_text[:200]}...")

    return _parse_response(response_text)


def analyze_with_openai(image_path: Path) -> AnalysisResult:
    """Analyze a controller image using OpenAI GPT-4 Vision API."""
    try:
        import openai  # noqa: PLC0415
    except ImportError as e:
        raise ImportError(
            "openai package is required. Install with: pip install openai"
        ) from e

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    client = openai.OpenAI(api_key=api_key)

    image_data = _load_image_as_base64(image_path)
    media_type = _get_media_type(image_path)

    _logger.info(f"Analyzing image with OpenAI: {image_path.name}")

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}",
                        },
                    },
                    {
                        "type": "text",
                        "text": ANALYSIS_PROMPT,
                    },
                ],
            },
        ],
    )

    response_text = response.choices[0].message.content
    _logger.debug(f"OpenAI response: {response_text[:200]}...")

    return _parse_response(response_text)


def analyze_image(image_path: Path, provider: str = "auto") -> AnalysisResult:
    """Analyze a controller image using the specified AI provider.

    Args:
        image_path: Path to the image file
        provider: "claude", "openai", or "auto" (tries claude first, then openai)

    Returns:
        AnalysisResult with detected controls
    """
    if provider == "claude":
        return analyze_with_claude(image_path)
    elif provider == "openai":
        return analyze_with_openai(image_path)
    elif provider == "auto":
        # Try Claude first, fall back to OpenAI
        if os.environ.get("ANTHROPIC_API_KEY"):
            try:
                return analyze_with_claude(image_path)
            except Exception as e:
                _logger.warning(f"Claude analysis failed: {e}, trying OpenAI...")

        if os.environ.get("OPENAI_API_KEY"):
            return analyze_with_openai(image_path)

        raise ValueError(
            "No AI API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable."
        )
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'claude', 'openai', or 'auto'.")
