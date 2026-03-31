"""Install and uninstall user output plugins.

Thin wrapper around the unified plugin_installer for backward compatibility.
"""

from pathlib import Path

from joystick_diagrams.plugins.plugin_installer import (
    install_plugin,
    uninstall_plugin,
    validate_plugin,
)


def install_output_plugin(source: Path) -> Path:
    """Install an output plugin from a folder or ZIP file."""
    return install_plugin(source, "output")


def uninstall_output_plugin(plugin_name: str, plugin_path: Path) -> None:
    """Remove a user-installed output plugin."""
    return uninstall_plugin(plugin_name, plugin_path, "output")


def validate_output_plugin(plugin_path: Path) -> tuple[bool, str]:
    """Validate that a plugin directory contains a loadable OutputPlugin."""
    return validate_plugin(plugin_path, "output")
