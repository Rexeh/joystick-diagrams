"""Workflow settings accessors read at call time (a dict stands in for the table)."""

from unittest.mock import patch

import pytest

from joystick_diagrams import workflow_settings as ws


@pytest.fixture
def store():
    values: dict[str, str] = {}

    def get_setting(key):
        return values.get(key)

    def add_update(key, value):
        values[key] = value

    with (
        patch("joystick_diagrams.db.db_settings.get_setting", side_effect=get_setting),
        patch(
            "joystick_diagrams.db.db_settings.add_update_setting_value",
            side_effect=add_update,
        ),
    ):
        yield values


def test_auto_read_on_launch_defaults_on(store):
    assert ws.get_auto_read_on_launch() is True
    ws.set_auto_read_on_launch(False)
    assert store[ws.AUTO_READ_ON_LAUNCH_SETTING_KEY] == "false"
    assert ws.get_auto_read_on_launch() is False
    store[ws.AUTO_READ_ON_LAUNCH_SETTING_KEY] = "garbage"
    assert ws.get_auto_read_on_launch() is True
    ws.set_auto_read_on_launch(True)
    assert ws.get_auto_read_on_launch() is True


def test_export_folder_has_no_default_and_must_exist(store, tmp_path):
    assert ws.get_export_folder() is None
    assert ws.get_export_folder_raw() is None
    ws.set_export_folder(tmp_path)
    assert ws.get_export_folder() == tmp_path
    assert store[ws.EXPORT_FOLDER_SETTING_KEY] == str(tmp_path)  # the old key, kept
    gone = tmp_path / "removed"
    ws.set_export_folder(str(gone))
    assert ws.get_export_folder() is None  # ask again
    assert ws.get_export_folder_raw() == str(gone)  # but say which one is gone
    ws.set_export_folder(None)
    assert ws.get_export_folder() is None and ws.get_export_folder_raw() is None


def test_export_ticks_round_trip_as_json(store):
    assert ws.get_export_ticks() == {}
    assert ws.is_export_ticked("guid|profile") is True
    ws.set_export_tick("guid|profile", False)
    ws.set_export_tick("guid|other", True)
    assert ws.get_export_ticks() == {"guid|other": True, "guid|profile": False}
    assert ws.is_export_ticked("guid|profile") is False
    assert ws.is_export_ticked("unknown", default=False) is False
    store[ws.EXPORT_TICKS_SETTING_KEY] = "not json"
    assert ws.get_export_ticks() == {}
    store[ws.EXPORT_TICKS_SETTING_KEY] = "[1, 2]"
    assert ws.get_export_ticks() == {}
    ws.set_export_ticks({"a": 1, "b": 0})
    assert ws.get_export_ticks() == {"a": True, "b": False}


def test_last_stage_is_an_int_within_the_strip(store):
    assert ws.get_last_stage() is None
    ws.set_last_stage(3)
    assert ws.get_last_stage() == 3
    ws.set_last_stage(9)
    assert ws.get_last_stage() == ws.LAST_STAGE_INDEX
    ws.set_last_stage(-1)
    assert ws.get_last_stage() == ws.FIRST_STAGE
    store[ws.LAST_STAGE_SETTING_KEY] = "two"
    assert ws.get_last_stage() is None
    store[ws.LAST_STAGE_SETTING_KEY] = "7"
    assert ws.get_last_stage() == ws.LAST_STAGE_INDEX
