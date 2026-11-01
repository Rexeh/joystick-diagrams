"""1. Setup: first-launch picker, folder card, game card states, results card."""

import os
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QLabel, QPushButton  # noqa: E402

from joystick_diagrams.plugins import plugin_catalog as pc  # noqa: E402
from joystick_diagrams.ui.setup_page import SetupPage, suggested_paths  # noqa: E402
from joystick_diagrams.ui.stage_contract import ReadOutcome  # noqa: E402
from tests.ui.stage_fixtures import (  # noqa: E402
    STICK,
    THROTTLE,
    FakeProfileWrapper,
    drain,
    fake_game_wrapper,
    patched_settings,
    profile_with,
    seed_app_state,
)


@pytest.fixture(autouse=True)
def _fresh_state(temp_database):
    with patched_settings():
        seed_app_state()
        yield
    drain()
    from joystick_diagrams.app_state import AppState

    AppState._inst = None


def make_page(qtbot, wrappers=(), profile_wrappers=()):
    state = seed_app_state(list(wrappers), list(profile_wrappers))
    with patch.object(SetupPage, "fetch_catalog", autospec=True):
        page = SetupPage()
    qtbot.addWidget(page)
    return page, state


def entry(name, signed=True):
    return pc.CatalogEntry(
        id=str(uuid4()),
        name=name,
        type="parser",
        version="1.0.0",
        download_url="https://example.com/p.zip",
        sha256="0" * 64,
        signed=signed,
    )


def texts(widget):
    return [label.text() for label in widget.findChildren(QLabel) if label.text()]


def buttons(widget):
    return {b.text(): b for b in widget.findChildren(QPushButton)}


# ── First launch ──


def test_first_launch_asks_which_games(qtbot):
    page, _ = make_page(qtbot)
    assert page.title_label.text() == "Which games do you play?"
    assert page.picker.isVisibleTo(page)
    action = page.next_action()
    assert action.label == "Choose a game to add" and not action.enabled
    assert page.footer_hint() == "You can add or remove games here at any time."
    assert page.stage_status().text == "Choose your games"


def test_ticking_games_names_the_add_button(qtbot):
    page, _ = make_page(qtbot)
    page.picker.set_entries(
        [entry("DCS World"), entry("Joystick Gremlin", signed=False)]
    )
    first, second = page.picker.cards
    qtbot.mouseClick(first, Qt.MouseButton.LeftButton)  # the whole card toggles
    assert first.checked and first.will_be_added.isVisibleTo(first)
    assert page.next_action().label == "Add DCS World and continue ›"
    second.checkbox.setChecked(True)
    assert page.next_action().label == "Add 2 games and continue ›"
    assert "Community" in " ".join(texts(second))
    with patch.object(page, "add_games") as add:
        page.next_action().callback()
    add.assert_called_once()
    assert [e.name for e in add.call_args.args[0]] == ["DCS World", "Joystick Gremlin"]


def test_offline_picker_offers_try_again_and_a_file(qtbot):
    page, _ = make_page(qtbot)
    page.picker.set_unavailable()
    assert "We couldn't load the list of games." in " ".join(texts(page.picker))
    assert "Try again" in buttons(page.picker)
    assert "Add a game from a file…" in buttons(page.picker)


# ── Folder card ──


def test_folder_card_shows_found_candidates_and_reads_on_use(qtbot, tmp_path):
    found = tmp_path / "Saved Games" / "DCS"
    other = tmp_path / "Saved Games" / "DCS.openbeta"
    found.mkdir(parents=True)
    other.mkdir(parents=True)
    wrapper = fake_game_wrapper([found, other, tmp_path / "missing"])
    page, _ = make_page(qtbot, [wrapper])
    assert suggested_paths(wrapper) == [found, other]
    card = page.cards["Test Game"]
    assert page.title_label.text() == "Where does Test Game keep your bindings?"
    assert card.status_label.text() == "Added · needs its folder"
    all_text = " ".join(texts(card))
    assert "Found" in all_text and str(found) in all_text
    assert "Also found" in all_text and "Last changed" in all_text
    labels = buttons(card)
    assert "Use this folder and read it" in labels
    assert "Use this one instead" in labels
    assert "Choose folder…" in labels
    assert page.stage_status().icon == "warning"
    assert page.stage_status().text == "Test Game needs its folder"
    assert page.footer_hint().startswith("Choose the folders first.")
    with qtbot.waitSignal(page.read_requested) as blocker:
        labels["Use this folder and read it"].click()
    assert blocker.args[0] == [wrapper]
    assert wrapper.ready
    assert page.cards["Test Game"].folder_label.text() == f"· {found}"


def test_no_candidate_falls_back_to_choose_folder(qtbot, tmp_path):
    wrapper = fake_game_wrapper([])
    page, _ = make_page(qtbot, [wrapper])
    card = page.cards["Test Game"]
    assert "Choose the folder where Test Game keeps your bindings." in " ".join(
        texts(card)
    )
    chosen = tmp_path / "picked"
    chosen.mkdir()
    with (
        patch(
            "joystick_diagrams.ui.setup_page.QFileDialog.getExistingDirectory",
            return_value=str(chosen),
        ),
        qtbot.waitSignal(page.read_requested),
    ):
        buttons(card)["Choose folder…"].click()
    assert wrapper.ready


# ── Read lifecycle ──


def _ready_page(qtbot, tmp_path, profiles=()):
    folder = tmp_path / "game"
    folder.mkdir()
    wrapper = fake_game_wrapper()
    wrapper.update_setting("game_dir", folder)
    page, state = make_page(qtbot, [wrapper], profiles)
    return page, wrapper, state


def test_reading_then_up_to_date(qtbot, tmp_path):
    page, wrapper, _ = _ready_page(qtbot, tmp_path)
    page.on_read_started(["Test Game"])
    assert page.stage_status().icon == "busy"
    assert page.stage_status().text == "Reading Test Game…"
    assert page.cards["Test Game"].status_label.text() == "Reading Test Game…"
    assert page.footer_hint() == "Stages 2 to 4 fill in when this finishes."
    page.on_read_finished(
        ReadOutcome(
            games=["Test Game"],
            finished_at="09:41",
            profiles_per_game={"Test Game": 12},
            profile_count=12,
        )
    )
    assert page.stage_status().icon == "ok"
    assert page.stage_status().text == "Up to date · read 09:41"
    assert page.cards["Test Game"].status_label.text() == "12 profiles · read 09:41"


def test_zero_profiles_turns_the_card_amber(qtbot, tmp_path):
    page, _, _ = _ready_page(qtbot, tmp_path)
    page.on_read_finished(
        ReadOutcome(games=["Test Game"], finished_at="09:41", profiles_per_game={})
    )
    status = page.stage_status()
    assert status.icon == "warning" and status.text == "No bindings in Test Game"
    card = page.cards["Test Game"]
    assert card.property("state") == "warning"
    assert card.status_label.text() == "No bindings found · read 09:41"
    assert any(t.startswith("We didn't find any bindings in") for t in texts(card))


def test_failed_read_says_what_is_kept(qtbot, tmp_path):
    page, _, _ = _ready_page(qtbot, tmp_path)
    page.on_read_finished(
        ReadOutcome(
            games=["Test Game"], failed={"Test Game": "boom"}, finished_at="09:41"
        )
    )
    assert page.stage_status().text == "Couldn't read Test Game"
    joined = " ".join(texts(page.cards["Test Game"]))
    assert "We couldn't read Test Game." in joined
    assert "Your templates, labels and layouts are kept." in joined
    assert {"Choose folder…", "Read again", "Details"} <= set(
        buttons(page.cards["Test Game"])
    )


def test_read_again_asks_the_shell(qtbot, tmp_path):
    page, wrapper, _ = _ready_page(qtbot, tmp_path)
    with qtbot.waitSignal(page.read_requested) as blocker:
        buttons(page.cards["Test Game"])["Read again"].click()
    assert blocker.args[0] == [wrapper]


# ── Results card ──


def test_results_card_counts_and_reasons(qtbot, tmp_path):
    profiles = [FakeProfileWrapper(profile_with("F-16C"), game="Joystick Gremlin")]
    page, wrapper, _ = _ready_page(qtbot, tmp_path, profiles)
    page.populate_plugin_cards()
    assert page.results_card.isVisibleTo(page)
    text = page.results_text()
    assert "We found 4 controllers in 1 profile" in text
    assert "need a template before they can be drawn" in text
    assert "Gladiator NXT" in text and "Warthog Throttle" in text
    assert "set to No diagram (change this in 2. Controllers)" in text
    assert "Keyboard" in text and "listed as a keyboard" not in text
    assert "vJoy Device (nothing bound)" in text
    assert text.count("A template is a picture of your controller") == 1
    action = page.next_action()
    assert action.label == "Next: Choose 3 templates ›"
    with qtbot.waitSignal(page.request_stage) as blocker:
        action.callback()
    assert blocker.args[0] == 1
    assert blocker.args[1]["device_guid"] in {STICK, THROTTLE}


def test_results_card_hidden_before_a_read(qtbot, tmp_path):
    page, _, _ = _ready_page(qtbot, tmp_path)
    assert not page.results_card.isVisibleTo(page)
    # Nothing read yet: reading is the next step, not an empty 2. Controllers
    action = page.next_action()
    assert action.label == "Read Test Game"
    with qtbot.waitSignal(page.read_requested):
        action.callback()
    assert page.stage_status().text == "Ready to read"


def test_turning_a_game_off_is_saved(qtbot, tmp_path):
    page, wrapper, state = _ready_page(qtbot, tmp_path)
    state.main_window = SimpleNamespace(statusLabel=None)
    page.cards["Test Game"].read_this.setChecked(False)
    drain()
    assert not wrapper.enabled
    assert page.cards["Test Game"].status_label.text() == "Not read · turned off"
