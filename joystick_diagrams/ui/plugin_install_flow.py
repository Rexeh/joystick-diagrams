"""Shared plugin install + trust flow used by the Settings page and the Plugin Store.

Wraps the post-install signing/trust check so both the manual "install from URL/ZIP"
flow and the catalog-driven store apply identical security handling.
"""

import logging
from pathlib import Path

from PySide6.QtWidgets import QWidget

_logger = logging.getLogger(__name__)


def run_security_check(installed_path: Path, plugin_name: str, parent: QWidget) -> bool:
    """Show the appropriate signing/trust dialog after installing a plugin.

    Returns True if the plugin is signed (auto-accepted) or the user accepted an
    unsigned plugin; False if the user cancelled.
    """
    from joystick_diagrams.plugins.plugin_signing import verify_plugin_signature
    from joystick_diagrams.ui.plugin_security_dialog import (
        PluginSecurityWarningDialog,
        PluginSignedDialog,
    )

    if verify_plugin_signature(installed_path):
        PluginSignedDialog(plugin_name, parent).exec()
        return True

    dialog = PluginSecurityWarningDialog(plugin_name, parent)
    return dialog.exec() == PluginSecurityWarningDialog.Accepted


def record_trust(plugin_name: str, plugin_type: str, installed_path: Path) -> None:
    """Persist the trust decision for a freshly installed plugin."""
    from joystick_diagrams.db.db_plugin_trust import set_plugin_trusted
    from joystick_diagrams.plugins.plugin_signing import verify_plugin_signature

    reason = (
        "signature_valid"
        if verify_plugin_signature(installed_path)
        else "user_accepted"
    )
    set_plugin_trusted(plugin_name, plugin_type, True, reason)


def reload_plugin_manager(app_state, plugin_type: str) -> None:
    """Rebuild the relevant plugin manager on the shared AppState after an install.

    Also refreshes the Setup page's plugin cards if it is present.
    """
    if plugin_type == "parser":
        from joystick_diagrams.plugins.plugin_manager import ParserPluginManager

        mgr = ParserPluginManager()
        mgr.load_discovered_plugins()
        mgr.create_plugin_wrappers()
        app_state.plugin_manager = mgr
    else:
        from joystick_diagrams.plugins.output_plugin_manager import OutputPluginManager

        mgr = OutputPluginManager()
        mgr.load_discovered_plugins()
        mgr.create_plugin_wrappers()
        app_state.output_plugin_manager = mgr

    main_window = getattr(app_state, "main_window", None)
    setup_page = getattr(main_window, "_setup_page", None)
    if setup_page is not None:
        setup_page.populate_plugin_cards()


def install_from_catalog(entry, app_state, parent: QWidget) -> str | None:
    """Install (or update) a plugin from a catalog entry, applying the full trust flow.

    Verifies the download against the entry's SHA-256, validates the plugin, checks for
    bundled-name conflicts, runs the signing/trust dialog, records trust, and reloads the
    relevant manager. Returns the installed plugin name on success, or None on
    failure/cancellation (surfacing a message box for user-facing errors).
    """
    import shutil

    from PySide6.QtWidgets import QMessageBox

    from joystick_diagrams.plugins.plugin_installer import (
        install_plugin,
        validate_plugin,
    )

    try:
        installed_path = install_plugin(
            entry.download_url, entry.type, expected_sha256=entry.sha256
        )
    except Exception as e:
        QMessageBox.warning(parent, "Install Failed", str(e))
        return None

    valid, msg = validate_plugin(installed_path, entry.type)
    if not valid:
        shutil.rmtree(installed_path, ignore_errors=True)
        QMessageBox.warning(parent, "Invalid Plugin", msg)
        return None

    manager = (
        app_state.plugin_manager
        if entry.type == "parser"
        else app_state.output_plugin_manager
    )
    if manager is not None:
        bundled_names = {
            w.name
            for w in manager.plugin_wrappers
            if not manager.is_user_plugin(w.name)
        }
        if msg in bundled_names:
            shutil.rmtree(installed_path, ignore_errors=True)
            QMessageBox.warning(
                parent,
                "Name Conflict",
                f"A bundled plugin named '{msg}' already exists.",
            )
            return None

    if not run_security_check(installed_path, msg, parent):
        shutil.rmtree(installed_path, ignore_errors=True)
        return None

    record_trust(msg, entry.type, installed_path)
    reload_plugin_manager(app_state, entry.type)
    return msg


def install_from_local_source(
    source: Path | str,
    app_state,
    parent: QWidget,
    plugin_type: str = "parser",
) -> str | None:
    """Install a plugin from a local ZIP/folder path or a URL, applying the full trust flow.

    Mirrors ``install_from_catalog`` but without a catalog entry, so there is no expected
    SHA-256 to verify against — the source is user-supplied. Validates the plugin, checks
    for bundled-name conflicts, runs the signing/trust dialog, records trust, and reloads
    the relevant manager. Returns the installed plugin name on success, or None on
    failure/cancellation (surfacing a message box for user-facing errors).
    """
    import shutil

    from PySide6.QtWidgets import QMessageBox

    from joystick_diagrams.plugins.plugin_installer import (
        install_plugin,
        validate_plugin,
    )

    try:
        installed_path = install_plugin(source, plugin_type)
    except Exception as e:
        QMessageBox.warning(parent, "Install Failed", str(e))
        return None

    valid, msg = validate_plugin(installed_path, plugin_type)
    if not valid:
        shutil.rmtree(installed_path, ignore_errors=True)
        QMessageBox.warning(parent, "Invalid Plugin", msg)
        return None

    manager = (
        app_state.plugin_manager
        if plugin_type == "parser"
        else app_state.output_plugin_manager
    )
    if manager is not None:
        bundled_names = {
            w.name
            for w in manager.plugin_wrappers
            if not manager.is_user_plugin(w.name)
        }
        if msg in bundled_names:
            shutil.rmtree(installed_path, ignore_errors=True)
            QMessageBox.warning(
                parent,
                "Name Conflict",
                f"A bundled plugin named '{msg}' already exists.",
            )
            return None

    if not run_security_check(installed_path, msg, parent):
        shutil.rmtree(installed_path, ignore_errors=True)
        return None

    record_trust(msg, plugin_type, installed_path)
    reload_plugin_manager(app_state, plugin_type)
    return msg
