"""Developer scaffolder for new Joystick Diagrams plugins.

Generates a ready-to-edit shell plugin (a package folder with ``__init__.py`` and
``main.py``) with an auto-generated GUID ``id`` written into its ``PluginMeta``. Exposed
as the ``create-plugin`` console script.

Usage:
    create-plugin "My Plugin" parser
    create-plugin "My Exporter" output --dest ./plugins
"""

import argparse
import re
import sys
from pathlib import Path
from uuid import uuid4

_PARSER_TEMPLATE = """from pathlib import Path

from pydantic import Field

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings


class Settings(PluginSettings):
    # Define your path/settings fields here. Required paths block ready state until set.
    source_dir: Path | None = Field(
        default=None,
        title="Source Folder",
        json_schema_extra={"is_folder": True, "default_path": "~/Saved Games"},
    )


class ParserPlugin(PluginInterface):
    plugin_meta = PluginMeta(
        id="__PLUGIN_ID__",  # stable identity — generated once, never change it
        name="__PLUGIN_NAME__",
        version="0.0.1",
        icon_path="img/logo.ico",
    )
    plugin_settings_model = Settings

    def __init__(self):
        super().__init__()

    def process(self) -> ProfileCollection:
        # Build and return a ProfileCollection from your source data.
        return ProfileCollection()

    def on_settings_loaded(self) -> None:
        # Rebuild any internal state from self.get_setting(...) here.
        pass
"""

_OUTPUT_TEMPLATE = """from joystick_diagrams.plugins.output_plugin_interface import (
    ExportResult,
    OutputPluginInterface,
)
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings


class Settings(PluginSettings):
    # Define any output settings here (optional).
    pass


class OutputPlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(
        id="__PLUGIN_ID__",  # stable identity — generated once, never change it
        name="__PLUGIN_NAME__",
        version="0.0.1",
        icon_path="img/logo.ico",
    )
    plugin_settings_model = Settings

    def __init__(self):
        super().__init__()

    def process_export(self, results: list[ExportResult]) -> bool:
        # Consume the exported results and return True on success.
        return True
"""

_TEMPLATES = {"parser": _PARSER_TEMPLATE, "output": _OUTPUT_TEMPLATE}


def slugify(name: str) -> str:
    """Turn a display name into a filesystem-safe folder slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "plugin"


def create_plugin(name: str, plugin_type: str, dest_root: Path | None = None) -> Path:
    """Scaffold a new plugin package and return its directory path.

    Generates a GUID id, writes __init__.py and a type-appropriate main.py, and an
    empty img/ folder for the plugin's icon. Raises ValueError on a bad type and
    FileExistsError if the target directory already exists.
    """
    if plugin_type not in _TEMPLATES:
        raise ValueError(
            f"Unknown plugin type '{plugin_type}'. Use 'parser' or 'output'."
        )

    dest_root = Path.cwd() if dest_root is None else Path(dest_root)
    folder_name = f"{slugify(name)}_plugin"
    dest = dest_root / folder_name
    if dest.exists():
        raise FileExistsError(f"Target plugin directory already exists: {dest}")

    plugin_id = uuid4()
    main_source = (
        _TEMPLATES[plugin_type]
        .replace("__PLUGIN_ID__", str(plugin_id))
        .replace("__PLUGIN_NAME__", name)
    )

    dest.mkdir(parents=True)
    (dest / "__init__.py").write_text("", encoding="utf-8")
    (dest / "main.py").write_text(main_source, encoding="utf-8")
    (dest / "img").mkdir()

    print(f"Created {plugin_type} plugin '{name}' at {dest}")
    print(f"  Plugin GUID: {plugin_id}")
    print("Next steps:")
    print(f"  1. Add an icon at {dest / 'img' / 'logo.ico'} (or update icon_path).")
    print("  2. Implement the plugin logic in main.py.")
    print("  3. Zip the folder, (optionally) sign it, and add an entry to")
    print("     plugins_manifest.json with the GUID above, the download URL, and the")
    print("     ZIP's SHA-256.")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="create-plugin",
        description="Scaffold a new Joystick Diagrams plugin with an auto-generated GUID.",
    )
    parser.add_argument("name", help='Display name for the plugin, e.g. "My Plugin"')
    parser.add_argument(
        "type", choices=["parser", "output"], help="Plugin type to scaffold"
    )
    parser.add_argument(
        "--dest",
        default=None,
        help="Directory to create the plugin folder in (default: current directory)",
    )
    args = parser.parse_args(argv)

    try:
        create_plugin(args.name, args.type, args.dest)
    except (ValueError, FileExistsError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
