"""Phase 3 (F4) behaviour: Settings, the game list and community check wording,
the Verified chip, the reason wording, the launch-read export queue, page rows
before a read, and the Qt message filter."""
# ruff: noqa: F811 (pytest fixtures imported from tests/ui/stage34_fixtures.py)

import logging
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QtMsgType  # noqa: E402

from joystick_diagrams import workflow_settings  # noqa: E402
from joystick_diagrams.device_status import (  # noqa: E402
    DeviceStatus,
    StatusInfo,
    reason_text,
)
from joystick_diagrams.ui import strings_diagrams as SD  # noqa: E402
from joystick_diagrams.ui import strings_settings as SS  # noqa: E402
from tests.ui.stage34_fixtures import (  # noqa: E402, F401
    PANEL,
    STICK,
    THROTTLE,
    FakeShell,
    _reset_app_state,
    seed_state,
    settings_store,
)

# ── Reasons: one wording, from device_status ──


def test_reason_wording_is_the_language_guide_one():
    assert reason_text("nothing_bound_moved") == (
        "Nothing bound: its bindings are on your stick"
    )
    assert reason_text("merged_into", merged_name="Stick") == "Same controller as Stick"
    from joystick_diagrams.ui import strings_controllers

    assert not hasattr(strings_controllers, "REASON_TEXT")
    assert not hasattr(strings_controllers, "reason_sentence")


# ── Verified chip: the game list decides ──


def _wrapper(name="DCS World"):
    return SimpleNamespace(name=name)


@pytest.mark.parametrize(
    ("trust", "listed", "expected"),
    [
        ("signature_valid", None, True),
        ("user_accepted", True, True),  # added from a folder, listed Verified
        ("user_accepted", False, False),
        ("user_accepted", None, False),
        (None, True, True),
        (None, None, None),
    ],
)
def test_verified_chip_reads_the_game_list(trust, listed, expected):
    from joystick_diagrams.ui import setup_page

    flags = {} if listed is None else {"DCS World": listed}
    with (
        patch(
            "joystick_diagrams.db.db_plugin_trust.get_trust_reason", return_value=trust
        ),
        patch.object(setup_page, "catalog_verified_flags", return_value=flags),
    ):
        assert setup_page.is_verified(_wrapper()) is expected


def test_game_list_flags_are_remembered(settings_store):
    from joystick_diagrams.ui import setup_page

    catalog = SimpleNamespace(
        plugins=[
            SimpleNamespace(name="DCS World", type="parser", signed=True),
            SimpleNamespace(name="Gremlin", type="parser", signed=False),
            SimpleNamespace(name="OpenKneeboard", type="output", signed=True),
        ]
    )
    assert setup_page.remember_catalog_flags(catalog)
    assert setup_page.catalog_verified_flags() == {"DCS World": True, "Gremlin": False}
    assert not setup_page.remember_catalog_flags(catalog)  # unchanged


# ── Community check and game list wording ──


def test_community_check_needs_the_trust_tick(qtbot):
    from joystick_diagrams.ui.plugin_security_dialog import (
        PluginSecurityWarningDialog,
    )

    dialog = PluginSecurityWarningDialog("Falcon BMS")
    qtbot.addWidget(dialog)
    assert dialog.windowTitle() == "Add a community game"
    assert dialog._acknowledge_check.text() == "I trust where Falcon BMS came from"
    assert dialog._install_btn.text() == "Add Falcon BMS"
    assert not dialog._install_btn.isEnabled()
    dialog._acknowledge_check.setChecked(True)
    assert dialog._install_btn.isEnabled()
    app = PluginSecurityWarningDialog("Kneeboard", for_app=True)
    qtbot.addWidget(app)
    assert app.windowTitle() == "Add a community app"


def test_verified_games_are_added_without_a_dialog(tmp_path):
    from joystick_diagrams.ui import plugin_install_flow as flow

    with (
        patch(
            "joystick_diagrams.plugins.plugin_signing.verify_plugin_signature",
            return_value=True,
        ),
        patch(
            "joystick_diagrams.ui.plugin_security_dialog.PluginSecurityWarningDialog"
        ) as dialog,
    ):
        assert flow.run_security_check(tmp_path, "DCS World", None)
    dialog.assert_not_called()


# ── Settings ──


@pytest.mark.uitest
def test_settings_has_general_and_other_apps(qtbot, settings_store):
    from joystick_diagrams.ui.settings_page import SettingsPage

    seed_state()
    page = SettingsPage()
    qtbot.addWidget(page)
    labels = [page.nav_list.item(i).text() for i in range(page.nav_list.count())]
    assert labels == [SS.NAV_GENERAL, SS.NAV_OTHER_APPS]
    assert page.auto_read_cb.isChecked()
    page.auto_read_cb.setChecked(False)
    assert workflow_settings.get_auto_read_on_launch() is False
    combo = page.alias_strategy_combo
    assert [combo.itemText(i) for i in range(combo.count())] == [
        "Show both on one line (A | B)",
        "Show one, list the other under it",
    ]


@pytest.mark.uitest
def test_removing_an_app_asks_with_the_verb(qtbot, settings_store):
    from joystick_diagrams.ui import settings_page

    seed_state()
    page = settings_page.SettingsPage()
    qtbot.addWidget(page)
    with patch.object(settings_page, "confirm", return_value=False) as ask:
        page._remove_app("OpenKneeboard")
    ask.assert_called_once()
    args = ask.call_args.args
    assert args[1:4] == (
        "Remove OpenKneeboard?",
        "Its settings are kept if you add it again.",
        "Remove OpenKneeboard",
    )


# ── Export: queued launch read, pages before a read ──


@pytest.mark.uitest
def test_launch_read_export_queues_from_last_time(qapp, settings_store, tmp_path):
    """Before the launch read finishes there are no bindings yet; with an export
    last time, Export still waits for the read instead of being disabled."""
    from joystick_diagrams.ui.diagrams_page import DiagramsPage

    seed_state(profiles={})  # nothing read yet
    shell = FakeShell()
    page = DiagramsPage(shell)
    page.refresh()
    screen = page.export_screen
    shell.read_in_progress = True
    page.on_read_started()  # the shell calls this when the read starts
    assert not page.next_action().enabled  # never exported: nothing to wait for
    assert page.stage_status().text == SD.STATUS_WAITING_FOR_READ
    assert screen.empty_label.text() == SD.WAITING_FOR_READ
    assert not screen.go_to_controllers_button.isVisibleTo(screen)

    from joystick_diagrams.ui.device_setup import store_last_export_keys

    store_last_export_keys(["device:x|profile"])
    action = page.next_action()
    assert action.label == SD.EXPORT_WHEN_READ_FINISHES and action.enabled
    action.callback()
    assert screen.queued
    assert page.stage_status().text == SD.STATUS_QUEUED


def test_page_waits_quietly_for_members_not_in_the_read():
    from joystick_diagrams.render.page import Page, Placement
    from joystick_diagrams.ui.device_setup import build_export_model

    page = Page(
        name="Stick and throttle",
        placements=[Placement(device_guid=STICK), Placement(device_guid=THROTTLE)],
    )
    unseen = {
        STICK: StatusInfo(DeviceStatus.NOT_SEEN),
        THROTTLE: StatusInfo(DeviceStatus.NOT_SEEN),
    }
    model = build_export_model([], unseen, [page])
    assert model.rows == [] and model.not_included == []
    needs = {
        STICK: StatusInfo(DeviceStatus.NOT_SEEN),
        THROTTLE: StatusInfo(DeviceStatus.NEEDS_TEMPLATE, name="Warthog Throttle"),
    }
    model = build_export_model([], needs, [page])
    assert "Not included: Stick and throttle · Warthog Throttle needs a template" in [
        n.text for n in model.not_included
    ]


# ── Qt messages ──


def test_thumbnail_noise_is_demoted_to_debug():
    from joystick_diagrams import qt_messages

    noise = "QPainter::begin: Paint device returned engine == 0, type: 3"
    assert qt_messages.is_noise(noise)
    assert qt_messages.level_for(QtMsgType.QtWarningMsg, noise) == logging.DEBUG
    assert (
        qt_messages.level_for(QtMsgType.QtWarningMsg, "Could not parse node: font")
        == logging.DEBUG
    )
    assert (
        qt_messages.level_for(QtMsgType.QtWarningMsg, "Something real happened")
        == logging.WARNING
    )
    assert qt_messages.level_for(QtMsgType.QtCriticalMsg, "bad") == logging.ERROR
