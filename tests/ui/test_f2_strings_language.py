"""The app's words follow docs/superpowers/specs/2026-10-25-ux-language.md.

Three nets, from cheapest to widest:

1. every ``ui/strings_*.py`` module (format placeholders such as ``{device}``
   are variable names, not words, and are stripped first);
2. every string literal in ``joystick_diagrams/ui/**`` passed straight to a Qt
   text API (``setText``, ``setToolTip``, ``QLabel(...)``, ``QMessageBox``…);
3. the text and tooltips of the built pages: the four stages, Settings, the
   template picker, the game list and the community check.

No exceptions: the upgrade banner no longer says "hidden".
"""

import ast
import importlib
import os
import pkgutil
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractButton,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
)

import joystick_diagrams.ui as ui_package  # noqa: E402
from joystick_diagrams.input.button import Button  # noqa: E402
from joystick_diagrams.input.profile import Profile_  # noqa: E402
from tests.ui.stage_fixtures import (  # noqa: E402
    STICK,
    FakeProfileWrapper,
    drain,
    patched_settings,
    seed_app_state,
)

BANNED = re.compile(
    r"\b(plugins?|devices?|binds?|alias(es)?|canonical|override|fallback|hidden)\b",
    re.IGNORECASE,
)
PLACEHOLDER = re.compile(r"\{[^{}]*\}")
UI_ROOT = Path(ui_package.__file__).parent

STRINGS_MODULES = sorted(
    info.name
    for info in pkgutil.iter_modules([str(UI_ROOT)])
    if info.name.startswith("strings_")
)


def banned_in(text: str) -> bool:
    return bool(BANNED.search(PLACEHOLDER.sub(" ", text)))


def _strings(module):
    for name, value in vars(module).items():
        if name.startswith("_") or not name.isupper():
            continue
        values = []
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, tuple):
            values = [v for v in value if isinstance(v, str)]
        elif isinstance(value, dict):
            values = [v for v in value.values() if isinstance(v, str)]
        for text in values:
            yield name, text


def test_every_stage_has_a_strings_module():
    for stage in ("setup", "controllers", "bindings", "diagrams", "shell"):
        assert f"strings_{stage}" in STRINGS_MODULES


@pytest.mark.parametrize("module_name", STRINGS_MODULES)
def test_no_banned_words_in_strings(module_name):
    module = importlib.import_module(f"joystick_diagrams.ui.{module_name}")
    offending = [(name, text) for name, text in _strings(module) if banned_in(text)]
    assert offending == []


@pytest.mark.parametrize("module_name", STRINGS_MODULES)
def test_no_dated_or_shouty_marks(module_name):
    module = importlib.import_module(f"joystick_diagrams.ui.{module_name}")
    for name, text in _strings(module):
        if name.endswith("_URL"):
            continue
        assert "!" not in text, name
        assert "(s)" not in text, name
        assert "..." not in text, name  # the ellipsis character only


# ── Literals handed straight to Qt ──

TEXT_APIS = {
    "setText",
    "setToolTip",
    "setPlaceholderText",
    "setWindowTitle",
    "setTitle",
    "setInformativeText",
    "setDetailedText",
    "setAccessibleName",
    "setStatusTip",
    "setSpecialValueText",
    "addTab",
    "addItem",
    "addItems",
    "addAction",
    "addButton",
    "setHeaderLabels",
    "information",
    "warning",
    "question",
    "critical",
    "about",
    "getText",
    "getOpenFileName",
    "getExistingDirectory",
    "QLabel",
    "QPushButton",
    "QCheckBox",
    "QRadioButton",
    "QAction",
    "QGroupBox",
    "QListWidgetItem",
    "show_banner",
    "set_status_text",
    "confirm",
    "show_problem",
}
LOGGERS = {"debug", "info", "warning", "error", "exception", "critical"}


def _ui_literals():
    for path in sorted(UI_ROOT.rglob("*.py")):
        if "qt_designer" in path.parts or path.name == "resources_rc.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else ""
            name = name or getattr(func, "id", "")
            if name not in TEXT_APIS:
                continue
            owner = func.value if isinstance(func, ast.Attribute) else None
            if name in LOGGERS and isinstance(owner, ast.Name) and "log" in owner.id:
                continue  # the log is for bug reports, not the player
            for arg in [*node.args, *(k.value for k in node.keywords)]:
                for sub in ast.walk(arg):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        yield f"{path.relative_to(UI_ROOT)}:{sub.lineno}", sub.value


def test_no_banned_words_in_ui_literals():
    offending = [(where, text) for where, text in _ui_literals() if banned_in(text)]
    assert offending == []


def test_the_dead_pages_are_gone():
    for name in ("configure_page", "customise_devices", "plugins_page"):
        assert not (UI_ROOT / f"{name}.py").exists(), name


# ── Built pages ──


@pytest.fixture(autouse=True)
def _fresh_state(temp_database):
    with patched_settings():
        yield
    drain()
    from joystick_diagrams.app_state import AppState

    AppState._inst = None


def _visible_texts(widget):
    texts = [w.text() for w in widget.findChildren(QLabel)]
    texts += [w.toolTip() for w in widget.findChildren(QLabel)]
    for button in widget.findChildren(QAbstractButton):
        texts += [button.text(), button.toolTip(), button.accessibleName()]
    texts += [w.title() for w in widget.findChildren(QGroupBox)]
    texts += [w.placeholderText() for w in widget.findChildren(QLineEdit)]
    for combo in widget.findChildren(QComboBox):
        texts += [combo.itemText(i) for i in range(combo.count())]
        texts.append(combo.toolTip())
    texts.append(widget.windowTitle())
    return [t for t in texts if t]


def test_built_pages_show_no_banned_words(qtbot):
    from unittest.mock import patch

    from joystick_diagrams.ui.bindings_page import BindingsPage
    from joystick_diagrams.ui.controllers_page import ControllersPage
    from joystick_diagrams.ui.diagrams_page import DiagramsPage
    from joystick_diagrams.ui.plugin_security_dialog import (
        PluginSecurityWarningDialog,
    )
    from joystick_diagrams.ui.plugin_store_dialog import PluginStoreDialog
    from joystick_diagrams.ui.settings_page import SettingsPage
    from joystick_diagrams.ui.setup_page import SetupPage
    from joystick_diagrams.ui.template_picker import TemplatePickerDialog

    profile = Profile_("F-16C")
    profile.add_device(STICK, "Gladiator NXT").create_input(Button(1), "Fire")
    seed_app_state(profile_wrappers=[FakeProfileWrapper(profile)])
    controllers = ControllersPage()
    controllers.more_button.setChecked(True)
    picker = TemplatePickerDialog(STICK)
    with patch.object(SetupPage, "fetch_catalog", autospec=True):
        setup = SetupPage()
    with patch.object(PluginStoreDialog, "_load", autospec=True):
        store = PluginStoreDialog()
    pages = [
        setup,
        controllers,
        picker,
        BindingsPage(),
        DiagramsPage(),
        SettingsPage(),
        store,
        PluginSecurityWarningDialog("Some Game"),
        PluginSecurityWarningDialog("Some App", for_app=True),
    ]
    for widget in pages:
        qtbot.addWidget(widget)
    for widget in pages:
        bad = [t for t in _visible_texts(widget) if banned_in(t)]
        assert bad == [], type(widget).__name__
    pages[4].shutdown()
