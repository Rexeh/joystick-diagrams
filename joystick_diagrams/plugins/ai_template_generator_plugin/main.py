"""AI Template Generator Plugin for Joystick Diagrams.

Analyzes images of gaming controllers using AI vision APIs (Claude/OpenAI)
and generates draw.io compatible SVG templates with proper placeholders
(BUTTON_X, AXIS_X, POV_X_Y etc.) for use with Joystick Diagrams.
"""

import json
import logging
from pathlib import Path

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.ai_template_generator_plugin.ai_analyzer import (
    analyze_image,
)
from joystick_diagrams.plugins.ai_template_generator_plugin.svg_generator import (
    generate_template,
    save_template,
)
from joystick_diagrams.plugins.plugin_interface import PluginInterface

from .config import settings

_logger = logging.getLogger(__name__)

CONFIG_FILE = "data.json"
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


class ParserPlugin(PluginInterface):
    def __init__(self):
        super().__init__()
        self.settings = settings
        self.settings.validators.register()
        self.path = None
        self.provider = "auto"
        self.generated_templates: list[Path] = []

    def process(self) -> ProfileCollection:
        """Analyze images in the selected folder and generate SVG templates.

        This plugin generates templates, not bindings. The ProfileCollection
        will be empty - the main output is SVG files in the templates directory.
        """
        if not self.path:
            _logger.error("No path set for AI Template Generator")
            return ProfileCollection()

        image_files = self._find_images(Path(self.path))

        if not image_files:
            _logger.warning(f"No image files found in {self.path}")
            return ProfileCollection()

        # Determine output directory (templates folder in project root)
        templates_dir = Path(__file__).resolve().parent.parent.parent.parent / "templates" / "AI Generated"

        self.generated_templates = []

        for image_path in image_files:
            try:
                _logger.info(f"Processing image: {image_path.name}")

                # Analyze the image with AI
                analysis = analyze_image(image_path, provider=self.provider)

                _logger.info(
                    f"Detected {len(analysis.controls)} controls "
                    f"on {analysis.device_name} ({analysis.device_type})"
                )

                # Generate SVG template
                svg_content = generate_template(analysis, image_path)

                # Save template
                output_path = save_template(svg_content, analysis.device_name, templates_dir)
                self.generated_templates.append(output_path)

                _logger.info(f"Template generated: {output_path}")

            except Exception as e:
                _logger.error(f"Failed to process {image_path.name}: {e}")

        _logger.info(f"Generated {len(self.generated_templates)} templates")

        # Return empty ProfileCollection since we generate templates, not bindings
        return ProfileCollection()

    def set_path(self, path: Path) -> bool:
        """Set and validate the folder containing controller images."""
        try:
            folder = Path(path)
            if not folder.is_dir():
                _logger.error(f"Path is not a directory: {path}")
                return False

            image_files = self._find_images(folder)
            if not image_files:
                _logger.warning(f"No supported image files found in: {path}")
                return False

            self.path = path
            self.save_plugin_state()
            _logger.info(f"Path set to {path} ({len(image_files)} images found)")
            return True

        except Exception as e:
            _logger.error(f"Error setting path: {e}")
            return False

    def save_plugin_state(self):
        """Persist plugin state to disk."""
        with open(
            Path.joinpath(self.get_plugin_data_path(), CONFIG_FILE),
            "w",
            encoding="UTF8",
        ) as f:
            f.write(
                json.dumps(
                    {
                        "path": str(self.path) if self.path else None,
                        "provider": self.provider,
                    }
                )
            )

    def load_settings(self) -> None:
        """Load persisted plugin settings."""
        try:
            with open(
                Path.joinpath(self.get_plugin_data_path(), CONFIG_FILE),
                "r",
                encoding="UTF8",
            ) as f:
                data = json.loads(f.read())
                self.path = Path(data["path"]) if data.get("path") else None
                self.provider = data.get("provider", "auto")
        except FileNotFoundError:
            pass

    @property
    def path_type(self):
        return self.FolderPath(
            "Select folder containing controller images (PNG/JPG)",
            Path.home(),
        )

    @property
    def icon(self):
        return f"{Path.joinpath(Path(__file__).parent, self.settings.PLUGIN_ICON)}"

    @staticmethod
    def _find_images(folder: Path) -> list[Path]:
        """Find all supported image files in a folder."""
        images = []
        for ext in SUPPORTED_IMAGE_EXTENSIONS:
            images.extend(folder.glob(f"*{ext}"))
            images.extend(folder.glob(f"*{ext.upper()}"))
        return sorted(set(images))
