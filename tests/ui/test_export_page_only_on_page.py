"""4. Diagrams › Export: "Export them only on this page" is authoritative.

A page with the flag ticked covers its controllers' profiles that it renders (its
own profile rule): those rows are unticked, disabled, "(on <page> page)" and never
exported, counted or ticked, whatever ticks are remembered. Other profiles stay
ordinary rows. With the flag off, every row behaves as before.
"""
# ruff: noqa: F811 (pytest fixtures imported from tests/ui/stage34_fixtures.py)

import os
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402

from joystick_diagrams import workflow_settings  # noqa: E402
from joystick_diagrams.render.page import ProfileRule  # noqa: E402
from joystick_diagrams.ui import strings_diagrams as S  # noqa: E402
from joystick_diagrams.ui.device_setup import (  # noqa: E402
    COLUMN_NAME,
    COLUMN_PROFILES,
    COLUMN_STATUS,
    controller_key,
    page_key,
    tick_key,
)
from joystick_diagrams.ui.diagrams_page import DiagramsPage  # noqa: E402
from joystick_diagrams.ui.export_page import ExportScreen  # noqa: E402
from tests.ui import stage34_fixtures  # noqa: E402
from tests.ui.stage34_fixtures import (  # noqa: E402, F401
    PANEL,
    STARTER_TEMPLATE,
    STICK,
    THROTTLE,
    FakeShell,
    _reset_app_state,
    seed_state,
    settings_store,
)

A10 = "dcs world_a-10c"
F16 = "dcs world_f-16c"
AH64 = "dcs world_ah-64d"
COMMON = "dcs world_common"
PAGE = "Stick + Throttle"
TIP = (
    "Exported on the Stick + Throttle page. Untick 'Export them only on this "
    "page' on the page to also export it on its own."
)

# Owner's scenario: the stick and the throttle share only A-10C; the stick also
# has F-16C, so a shared-rule page renders A-10C alone.
SHARED_A10 = {
    "F-16C": {STICK: {2: ("Trigger", [])}},
    "A-10C": {STICK: {1: ("Fire", [])}, THROTTLE: {1: ("Speed brake", [])}},
}


def _seed(profiles, names=None, templates=None):
    with patch.dict(stage34_fixtures.NAMES, names or {}):
        return seed_state(profiles=profiles, templates=templates)


_SHELLS = []  # the shell owns the page: keep it alive for the test


def _open(remembered=None):
    if remembered:
        workflow_settings.set_export_ticks(remembered)
    shell = FakeShell()
    _SHELLS[:] = [shell]
    page = DiagramsPage(shell)
    page.refresh()
    return page


def _item(screen, row_key):
    tree = screen.export_list.treeWidget
    for i in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(i)
        if item.data(COLUMN_NAME, Qt.ItemDataRole.UserRole) == row_key:
            return item
    raise AssertionError(f"no row {row_key}")


def _child(item, profile_name):
    for j in range(item.childCount()):
        child = item.child(j)
        if child.text(COLUMN_NAME).endswith(f"/ {profile_name}"):
            return child
    raise AssertionError(f"no profile {profile_name}")


def _job(screen, tmp_path):
    jobs = []
    with (
        patch.object(ExportScreen, "resolve_folder", return_value=Path(tmp_path)),
        patch.object(ExportScreen, "_run", lambda self, job, keys: jobs.append(job)),
    ):
        assert screen.start_export()
    (job,) = jobs
    devices = sorted((d.device_id, d.profile_wrapper.profile_key) for d in job.devices)
    pages = sorted((p.name, w.profile_key) for p, w in job.pages)
    return devices, pages


def _all_ticked(state, page_id=None):
    keys = {
        tick_key(controller_key(STICK), A10): True,
        tick_key(controller_key(STICK), F16): True,
        tick_key(controller_key(THROTTLE), A10): True,
    }
    if page_id:
        keys[tick_key(page_key(page_id), A10)] = True
    return keys


@pytest.mark.uitest
def test_shared_page_covers_its_profile_even_with_remembered_ticks(
    qapp, settings_store, tmp_path
):
    state = _seed(SHARED_A10)
    created = state.page_service.create(PAGE, [STICK, THROTTLE])
    assert created.profile_rule is ProfileRule.SHARED
    assert not created.export_members_separately
    page = _open(_all_ticked(state, created.page_id))
    screen = page.export_screen

    devices, pages = _job(screen, tmp_path)
    assert pages == [(PAGE, A10)]
    assert devices == [(STICK, F16)]  # not the stick's or throttle's A-10C
    assert screen.export_count() == 2
    assert page.next_action().label == "Export 2 diagrams"
    # The remembered ticks are kept, not overwritten
    stored = workflow_settings.get_export_ticks()
    assert stored[tick_key(controller_key(STICK), A10)] is True
    assert stored[tick_key(controller_key(THROTTLE), A10)] is True


@pytest.mark.uitest
def test_flag_off_exports_all_three(qapp, settings_store, tmp_path):
    state = _seed(SHARED_A10)
    created = state.page_service.create(
        PAGE, [STICK, THROTTLE], export_members_separately=True
    )
    page = _open(_all_ticked(state, created.page_id))
    screen = page.export_screen
    devices, pages = _job(screen, tmp_path)
    assert pages == [(PAGE, A10)]
    assert devices == [(STICK, A10), (STICK, F16), (THROTTLE, A10)]
    assert page.next_action().label == "Export 4 diagrams"
    stick = _item(screen, controller_key(STICK))
    assert _child(stick, "A-10C").flags() & Qt.ItemFlag.ItemIsEnabled
    assert _item(screen, controller_key(THROTTLE)).text(COLUMN_STATUS) == S.ROW_READY


@pytest.mark.uitest
def test_covered_rows_are_disabled_with_status_and_tooltip(qapp, settings_store):
    state = _seed(SHARED_A10)
    state.page_service.create(PAGE, [STICK, THROTTLE])
    screen = _open().export_screen

    stick = _item(screen, controller_key(STICK))
    a10 = _child(stick, "A-10C")
    assert a10.checkState(COLUMN_NAME) == Qt.CheckState.Unchecked
    assert not a10.flags() & Qt.ItemFlag.ItemIsEnabled
    assert not a10.flags() & Qt.ItemFlag.ItemIsUserCheckable
    assert a10.text(COLUMN_STATUS) == "(on Stick + Throttle page)"
    assert a10.toolTip(COLUMN_STATUS) == TIP
    f16 = _child(stick, "F-16C")
    assert f16.flags() & Qt.ItemFlag.ItemIsEnabled
    assert f16.checkState(COLUMN_NAME) == Qt.CheckState.Checked
    assert stick.text(COLUMN_STATUS) != "(on Stick + Throttle page)"
    assert stick.text(COLUMN_PROFILES) == "1 of 2"

    # Every throttle profile is covered: the controller row says so
    throttle = _item(screen, controller_key(THROTTLE))
    assert screen.model.row(controller_key(THROTTLE)).on_page == PAGE
    assert throttle.text(COLUMN_STATUS) == "(on Stick + Throttle page)"
    assert throttle.toolTip(COLUMN_STATUS) == TIP
    assert throttle.text(COLUMN_PROFILES) == "0 of 1"
    assert not throttle.flags() & Qt.ItemFlag.ItemIsUserCheckable


@pytest.mark.uitest
def test_tick_all_and_row_ticks_skip_covered_rows(qapp, settings_store):
    state = _seed(SHARED_A10)
    created = state.page_service.create(PAGE, [STICK, THROTTLE])
    page = _open()
    screen = page.export_screen
    export_list = screen.export_list
    covered = tick_key(controller_key(STICK), A10)

    export_list.tick_none()
    assert export_list.ticked_count() == 0
    assert page.next_action().label == S.EXPORT_DISABLED
    export_list.tick_all()
    assert covered not in export_list.ticked_keys()
    assert export_list.ticked_count() == 2
    assert page.next_action().label == "Export 2 diagrams"

    # Ticking the stick's row ticks its tickable profiles only
    stick = _item(screen, controller_key(STICK))
    stick.setCheckState(COLUMN_NAME, Qt.CheckState.Unchecked)
    export_list.flush()
    assert export_list.ticked_keys() == [tick_key(page_key(created.page_id), A10)]
    assert stick.checkState(COLUMN_NAME) == Qt.CheckState.Unchecked
    stick.setCheckState(COLUMN_NAME, Qt.CheckState.Checked)
    export_list.flush()
    assert tick_key(controller_key(STICK), F16) in export_list.ticked_keys()
    assert covered not in export_list.ticked_keys()
    assert _child(stick, "A-10C").checkState(COLUMN_NAME) == Qt.CheckState.Unchecked
    assert stick.checkState(COLUMN_NAME) == Qt.CheckState.Checked
    export_list.tick_same_as_last()  # nothing exported yet: nothing ticked
    assert covered not in export_list.ticked_keys()


@pytest.mark.uitest
def test_rows_return_when_the_page_goes_or_its_flag_changes(qapp, settings_store):
    state = _seed(SHARED_A10)
    created = state.page_service.create(PAGE, [STICK, THROTTLE])
    remembered = {tick_key(controller_key(STICK), A10): False}
    page = _open(remembered)
    screen = page.export_screen
    covered = tick_key(controller_key(STICK), A10)
    throttle_a10 = tick_key(controller_key(THROTTLE), A10)
    assert covered not in screen.export_list.ticked_keys()
    screen.export_list.tick_all()

    # Flag off: the remembered (False) and default (True) states come back
    state.page_service.save(
        state.page_service.get(created.page_id).model_copy(
            update={"export_members_separately": True}
        )
    )
    screen.refresh()
    ticked = screen.export_list.ticked_keys()
    assert covered not in ticked
    assert throttle_a10 in ticked
    row = _item(screen, controller_key(STICK))
    assert _child(row, "A-10C").flags() & Qt.ItemFlag.ItemIsEnabled

    # Back on, then the rule changes to "any": A-10C and F-16C both covered
    state.page_service.save(
        state.page_service.get(created.page_id).model_copy(
            update={
                "export_members_separately": False,
                "profile_rule": ProfileRule.ANY,
            }
        )
    )
    screen.refresh()
    assert screen.model.row(controller_key(STICK)).on_page == PAGE
    assert set(screen.export_list.ticked_keys()) == {
        tick_key(page_key(created.page_id), A10),
        tick_key(page_key(created.page_id), F16),
    }

    # Deleted: back to remembered/default
    state.page_service.delete(created.page_id)
    screen.refresh()
    ticked = screen.export_list.ticked_keys()
    assert covered not in ticked  # remembered unticked
    assert throttle_a10 in ticked and tick_key(controller_key(STICK), F16) in ticked


@pytest.mark.uitest
def test_two_pages_cover_the_union(qapp, settings_store):
    profiles = {
        "F-16C": {STICK: {2: ("Trigger", [])}, PANEL: {1: ("Lights", [])}},
        "A-10C": {STICK: {1: ("Fire", [])}, THROTTLE: {1: ("Speed brake", [])}},
        "Common": {STICK: {2: ("Comms", [])}},
    }
    templates = {s: STARTER_TEMPLATE for s in (STICK, THROTTLE, PANEL)}
    state = _seed(profiles, templates=templates)
    state.page_service.create(PAGE, [STICK, THROTTLE])  # A-10C
    state.page_service.create("Stick + Box", [STICK, PANEL])  # F-16C
    state.page_service.create(
        "Both", [STICK, THROTTLE, PANEL], profile_rule=ProfileRule.ANY
    )
    page = _open()
    screen = page.export_screen
    model = screen.model
    stick = model.row(controller_key(STICK))
    covered = {p.profile_key: p.covered_by for p in stick.profiles}
    # "Both" (rule "any") covers every profile one of them is bound in
    # Pages in list order (by name): the status names the first, "+N more"
    assert [p.name for p in state.page_service.pages()] == [
        "Both",
        "Stick + Box",
        PAGE,
    ]
    assert covered[A10] == ["Both", PAGE]
    assert covered[F16] == ["Both", "Stick + Box"]
    assert covered[COMMON] == ["Both"]
    assert stick.on_page == "Both"
    assert stick.on_pages == ["Both", "Stick + Box", PAGE]
    item = _item(screen, controller_key(STICK))
    assert item.text(COLUMN_STATUS) == "(on Both page +2 more)"
    assert _child(item, "A-10C").text(COLUMN_STATUS) == "(on Both page +1 more)"
    assert (
        _child(item, "A-10C")
        .toolTip(COLUMN_STATUS)
        .startswith("Exported on the Both page.")
    )
    assert _child(item, "Common").text(COLUMN_STATUS) == "(on Both page)"
    assert not any(k.startswith(controller_key(STICK)) for k in model.tick_keys)


@pytest.mark.uitest
def test_two_pages_union_leaves_uncovered_profiles(qapp, settings_store, tmp_path):
    profiles = {
        "F-16C": {STICK: {2: ("Trigger", [])}, PANEL: {1: ("Lights", [])}},
        "A-10C": {STICK: {1: ("Fire", [])}, THROTTLE: {1: ("Speed brake", [])}},
        "Common": {STICK: {2: ("Comms", [])}},
    }
    templates = {s: STARTER_TEMPLATE for s in (STICK, THROTTLE, PANEL)}
    state = _seed(profiles, templates=templates)
    state.page_service.create(PAGE, [STICK, THROTTLE])  # A-10C
    state.page_service.create("Stick + Box", [STICK, PANEL])  # F-16C
    page = _open()
    screen = page.export_screen
    item = _item(screen, controller_key(STICK))
    assert _child(item, "A-10C").text(COLUMN_STATUS) == "(on Stick + Throttle page)"
    assert _child(item, "F-16C").text(COLUMN_STATUS) == "(on Stick + Box page)"
    assert _child(item, "Common").flags() & Qt.ItemFlag.ItemIsEnabled
    assert item.text(COLUMN_PROFILES) == "1 of 3"
    devices, pages = _job(screen, tmp_path)
    assert devices == [(STICK, COMMON)]
    assert pages == [("Stick + Box", F16), (PAGE, A10)]
    assert page.next_action().label == "Export 3 diagrams"


@pytest.mark.uitest
def test_owner_screenshot_scenario(qapp, settings_store, tmp_path):
    """VKB (4 profiles) + Virpil (A-10C) on a shared page; a Warthog throttle
    elsewhere. Before: page 1 of 1, VKB 1 of 4, Virpil 1 of 1, throttle 0 of 1,
    "Export 3 diagrams" from remembered ticks. Now only the page is exported."""
    vkb, virpil, warthog = STICK, PANEL, THROTTLE
    names = {
        vkb: "VKBsim Gladiator NXT R",
        virpil: "VPC Constellation ALPHA-R",
        warthog: "Throttle - HOTAS Warthog",
    }
    profiles = {
        "A-10C": {vkb: {1: ("Fire", [])}, virpil: {1: ("Gear", [])}},
        "F-16C": {vkb: {2: ("Trigger", [])}},
        "AH-64D": {vkb: {2: ("Laser", [])}},
        "Common": {vkb: {1: ("Comms", [])}, warthog: {1: ("Speed brake", [])}},
    }
    templates = {s: STARTER_TEMPLATE for s in names}
    state = _seed(profiles, names=names, templates=templates)
    page_name = f"{names[vkb]} + {names[virpil]}"
    created = state.page_service.create(page_name, [vkb, virpil])
    assert created.profile_rule is ProfileRule.SHARED
    remembered = {
        tick_key(page_key(created.page_id), A10): True,
        tick_key(controller_key(vkb), A10): True,
        tick_key(controller_key(vkb), F16): False,
        tick_key(controller_key(vkb), AH64): False,
        tick_key(controller_key(vkb), COMMON): False,
        tick_key(controller_key(virpil), A10): True,
        tick_key(controller_key(warthog), COMMON): False,
    }
    page = _open(remembered)
    screen = page.export_screen
    on_page = f"(on {page_name} page)"

    page_item = _item(screen, page_key(created.page_id))
    assert page_item.text(COLUMN_NAME).endswith("· 1 profile")
    assert page_item.text(COLUMN_PROFILES) == "1 of 1"
    vkb_item = _item(screen, controller_key(vkb))
    assert vkb_item.text(COLUMN_PROFILES) == "0 of 4"
    a10 = _child(vkb_item, "A-10C")
    assert a10.text(COLUMN_STATUS) == on_page
    assert not a10.flags() & Qt.ItemFlag.ItemIsEnabled
    for name in ("F-16C", "AH-64D", "Common"):
        child = _child(vkb_item, name)
        assert child.flags() & Qt.ItemFlag.ItemIsEnabled
        assert child.flags() & Qt.ItemFlag.ItemIsUserCheckable
        assert child.checkState(COLUMN_NAME) == Qt.CheckState.Unchecked
    virpil_item = _item(screen, controller_key(virpil))
    assert virpil_item.text(COLUMN_PROFILES) == "0 of 1"
    assert virpil_item.text(COLUMN_STATUS) == on_page
    assert not _child(virpil_item, "A-10C").flags() & Qt.ItemFlag.ItemIsEnabled
    assert _item(screen, controller_key(warthog)).text(COLUMN_PROFILES) == "0 of 1"
    assert page.next_action().label == "Export 1 diagram"
    devices, pages = _job(screen, tmp_path)
    assert devices == [] and pages == [(page_name, A10)]

    # The other three VKB profiles can still be ticked
    _child(vkb_item, "F-16C").setCheckState(COLUMN_NAME, Qt.CheckState.Checked)
    screen.export_list.flush()
    assert vkb_item.text(COLUMN_PROFILES) == "1 of 4"
    assert vkb_item.checkState(COLUMN_NAME) == Qt.CheckState.PartiallyChecked
    assert page.next_action().label == "Export 2 diagrams"


@pytest.mark.uitest
def test_pages_dialog_explains_the_flag(qapp, settings_store):
    from joystick_diagrams.ui.pages_dialog import PagesDialog

    seed_state()
    dialog = PagesDialog(live_preview=False)
    assert dialog.only_on_page.text() == S.COMBINE_ONLY_ON_PAGE
    assert dialog.only_on_page_help.text() == (
        "Its controllers' own diagrams are skipped for the profiles this page covers."
    )
