"""Adding a game or other app (a plugin, in code): one flow for 1. Setup, the
game list dialog and Settings › Other apps.

Wraps the post-install signing/trust check so a file, a web address and the
game list apply identical security handling. Problems are one plain sentence,
with the system text behind Details (``show_problem``).
"""

import logging
from pathlib import Path

from PySide6.QtWidgets import QWidget

from joystick_diagrams.ui import strings_setup as S
from joystick_diagrams.ui.widgets.confirm import show_problem

_logger = logging.getLogger(__name__)


def _failed_title(plugin_type: str) -> str:
    return S.ADD_FAILED_TITLE if plugin_type == "parser" else S.ADD_FAILED_TITLE_APP


def _invalid_text(plugin_type: str) -> str:
    return S.ADD_FAILED_INVALID if plugin_type == "parser" else S.ADD_FAILED_INVALID_APP


def run_security_check(
    installed_path: Path, plugin_name: str, parent: QWidget, for_app: bool = False
) -> bool:
    """True when the plugin is signed (Verified: added without a dialog) or the
    player ticked "I trust where … came from"; False if they cancelled."""
    from joystick_diagrams.plugins.plugin_signing import verify_plugin_signature
    from joystick_diagrams.ui.plugin_security_dialog import (
        PluginSecurityWarningDialog,
    )

    if verify_plugin_signature(installed_path):
        return True

    dialog = PluginSecurityWarningDialog(plugin_name, parent, for_app=for_app)
    return dialog.exec() == PluginSecurityWarningDialog.DialogCode.Accepted


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

    _refresh_setup_page(app_state)


def _refresh_setup_page(app_state) -> None:
    """Rebuild the Setup page's plugin cards, if that page has been created."""
    main_window = getattr(app_state, "main_window", None)
    setup_page = getattr(main_window, "setup_page", None)
    if setup_page is not None:
        setup_page.populate_plugin_cards()


def plugin_config_key(plugin_name: str, plugin_type: str) -> str:
    """The key a plugin's configuration row is stored under, per plugin type.

    Parsers persist under their bare name (``PluginWrapper.store_plugin_configuration``)
    but output plugins are namespaced with ``_DB_PREFIX``
    (``OutputPluginWrapper._db_key``), so the two types can share a name without
    colliding. The prefix is imported rather than restated — a second copy of
    ``"output:"`` is how these drift apart later.
    """
    from joystick_diagrams.output_plugin_wrapper import _DB_PREFIX

    return plugin_name if plugin_type == "parser" else f"{_DB_PREFIX}{plugin_name}"


def has_stored_plugin_choice(plugin_name: str, plugin_type: str) -> bool:
    """True when a configuration row already exists for this plugin name and type.

    A row means this installation already holds an enabled/disabled choice for the
    plugin — either one the user made explicitly, or the default written the first
    time the plugin was wrapped. Either way the plugin is not new here, so
    auto-enabling it would overwrite a decision rather than make one.

    **Type-aware by necessity.** Output plugins persist under ``output:<name>``, so a
    bare-name lookup can never see an output plugin's row: it would report every
    output plugin as new and auto-enable it on every update, and would also mistake a
    genuinely new output plugin for a pre-existing *parser* of the same name.

    **Must be sampled before ``reload_plugin_manager``.** That call rebuilds the
    manager via ``create_plugin_wrappers()``, and ``setup_plugin`` inserts a
    configuration row for any plugin that lacks one — so after the reload a brand-new
    plugin is indistinguishable from one configured months ago, and this check would
    refuse to enable anything.
    """
    from joystick_diagrams.db.db_plugin_data import get_plugin_configuration

    return (
        get_plugin_configuration(plugin_config_key(plugin_name, plugin_type))
        is not None
    )


def enable_installed_plugin(app_state, plugin_type: str, plugin_name: str) -> None:
    """Enable a freshly installed plugin so it is immediately runnable.

    Choosing a plugin — from the catalog picker, the store, or a local ZIP — is an
    unambiguous statement of intent, so the user should not have to hunt for a second
    toggle before the Run button comes alive.

    **First installs only.** Callers must gate this on ``has_stored_plugin_choice``:
    ``install_from_catalog`` is also the *update* path (the store wires
    ``UPDATE_AVAILABLE`` straight to it), and a local reinstall can land on top of an
    existing plugin, so calling this unconditionally would silently re-enable a plugin
    the user had deliberately switched off.

    Must be called *after* ``reload_plugin_manager``: the wrapper this enables is
    created by that rebuild. Setting ``enabled`` persists via the wrapper's property
    setter, so the Setup page is refreshed again afterwards to pick up the new state.
    A wrapper that cannot be found is logged, not raised — the install itself
    succeeded and must not be reported as a failure.
    """
    manager = (
        app_state.plugin_manager
        if plugin_type == "parser"
        else app_state.output_plugin_manager
    )
    wrappers = getattr(manager, "plugin_wrappers", None) or []
    wrapper = next((w for w in wrappers if w.name == plugin_name), None)
    if wrapper is None:
        _logger.warning(
            f"Installed plugin '{plugin_name}' was not found after reloading the "
            f"{plugin_type} plugin manager - leaving it disabled."
        )
        return

    wrapper.enabled = True
    _refresh_setup_page(app_state)


def install_from_catalog(entry, app_state, parent: QWidget) -> str | None:
    """Install (or update) a plugin from a catalog entry, applying the full trust flow.

    Verifies the download against the entry's SHA-256, validates the plugin, checks for
    bundled-name conflicts, runs the signing/trust dialog, records trust, and reloads the
    relevant manager. Returns the installed plugin name on success, or None on
    failure/cancellation (surfacing a message box for user-facing errors).
    """
    import shutil

    from joystick_diagrams.plugins.plugin_installer import (
        install_plugin,
        validate_plugin,
    )

    title = _failed_title(entry.type)
    try:
        installed_path = install_plugin(
            entry.download_url, entry.type, expected_sha256=entry.sha256
        )
    except Exception as e:  # noqa: BLE001 - shown behind Details
        _logger.error(f"Adding {entry.name} failed: {e}", exc_info=True)
        show_problem(
            parent, title, S.ADD_FAILED_DOWNLOAD.format(name=entry.name), str(e)
        )
        return None

    valid, msg = validate_plugin(installed_path, entry.type)
    if not valid:
        shutil.rmtree(installed_path, ignore_errors=True)
        show_problem(parent, title, _invalid_text(entry.type), msg)
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
            show_problem(parent, title, S.ADD_NAME_TAKEN.format(name=msg))
            return None

    if not run_security_check(
        installed_path, msg, parent, for_app=entry.type != "parser"
    ):
        shutil.rmtree(installed_path, ignore_errors=True)
        return None

    # Sampled before the reload — see has_stored_plugin_choice. This is also the
    # update path (the store wires "Update -> vX" straight here), so a plugin the
    # user already has a choice for must keep it.
    is_first_install = not has_stored_plugin_choice(msg, entry.type)

    record_trust(msg, entry.type, installed_path)
    reload_plugin_manager(app_state, entry.type)
    if is_first_install:
        enable_installed_plugin(app_state, entry.type, msg)
    return msg


def install_from_local_source(
    source: Path | str,
    app_state,
    parent: QWidget,
    plugin_type: str = "parser",
) -> str | None:
    """Install a plugin from a local ZIP/folder path or a URL, applying the full trust flow.

    Mirrors ``install_from_catalog`` but without a catalog entry, so there is no expected
    SHA-256 to verify against — the source is user-supplied. Validates the plugin, runs
    the signing/trust dialog, records trust, and reloads the relevant manager. Returns the
    installed plugin name on success, or None on failure/cancellation (surfacing a message
    box for user-facing errors).
    """
    import shutil

    from joystick_diagrams.plugins.plugin_installer import (
        install_plugin,
        validate_plugin,
    )

    title = _failed_title(plugin_type)
    try:
        installed_path = install_plugin(source, plugin_type)
    except Exception as e:  # noqa: BLE001 - shown behind Details
        _logger.error(f"Adding {source} failed: {e}", exc_info=True)
        show_problem(parent, title, S.ADD_FAILED_FILE, str(e))
        return None

    valid, msg = validate_plugin(installed_path, plugin_type)
    if not valid:
        shutil.rmtree(installed_path, ignore_errors=True)
        show_problem(parent, title, _invalid_text(plugin_type), msg)
        return None

    # No bundled-name conflict check: every installed plugin is user-installed
    # since the plugins moved to their own repos, so there are no bundled names
    # to collide with.

    if not run_security_check(
        installed_path, msg, parent, for_app=plugin_type != "parser"
    ):
        shutil.rmtree(installed_path, ignore_errors=True)
        return None

    # Sampled before the reload — see has_stored_plugin_choice. Reinstalling over an
    # existing plugin must not resurrect it: uninstall deliberately leaves the
    # configuration row behind ("Plugin settings will be preserved").
    is_first_install = not has_stored_plugin_choice(msg, plugin_type)

    record_trust(msg, plugin_type, installed_path)
    reload_plugin_manager(app_state, plugin_type)
    if is_first_install:
        enable_installed_plugin(app_state, plugin_type, msg)
    return msg
