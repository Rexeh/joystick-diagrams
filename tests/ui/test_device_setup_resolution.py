"""``device_setup_controller`` keeps a missing template as a status instead of deleting it."""

import os
import shutil

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.db.db_device_management import (  # noqa: E402
    get_device_template_path,
)
from joystick_diagrams.ui.device_setup_controller import (  # noqa: E402
    get_export_devices,
    get_template_for_device,
    resolve_device_template,
)
from tests.ui.layout_fixtures import (  # noqa: E402
    DEVICE_GUID,
    STARTER_TEMPLATE,
    seed_layout_state,
)


@pytest.fixture(autouse=True)
def _reset_app_state():
    from joystick_diagrams.app_state import AppState

    AppState._inst = None
    yield
    AppState._inst = None


def test_unchosen_template_is_none(tmp_path):
    seed_layout_state(assign_template=False)
    assert resolve_device_template(DEVICE_GUID).status == "none"
    assert get_template_for_device(DEVICE_GUID) is None
    devices = get_export_devices()
    assert all(not d.has_template and not d.template_missing for d in devices)


def test_missing_template_is_reported_and_kept(tmp_path):
    gone = tmp_path / "Gone.svg"
    shutil.copy(STARTER_TEMPLATE, gone)
    gone.write_bytes(gone.read_bytes() + b"\n<!-- unique -->\n")  # no sha256 twin
    seed_layout_state(template_path=gone)
    gone.unlink()
    resolution = resolve_device_template(DEVICE_GUID)
    assert resolution.status == "missing" and resolution.file_name == "Gone.svg"
    assert get_template_for_device(DEVICE_GUID) is None
    devices = get_export_devices()
    assert devices and all(d.template_missing and not d.has_template for d in devices)
    # The stored choice survives (no silent delete)
    assert get_device_template_path(DEVICE_GUID) == str(gone)


def test_moved_template_is_relinked_for_export(tmp_path, monkeypatch):
    mine = tmp_path / "My templates"
    mine.mkdir()
    monkeypatch.setattr(
        "joystick_diagrams.template_identity.user_templates_root", lambda: mine
    )
    old = tmp_path / "old" / "Mine.svg"
    old.parent.mkdir()
    shutil.copy(STARTER_TEMPLATE, old)
    seed_layout_state(template_path=old)
    shutil.move(old, mine / "Mine.svg")
    resolution = resolve_device_template(DEVICE_GUID)
    assert resolution.status == "relinked" and resolution.path == mine / "Mine.svg"
    assert get_device_template_path(DEVICE_GUID) == str(mine / "Mine.svg")
    devices = get_export_devices()
    assert devices and all(d.has_template and not d.template_missing for d in devices)
    assert devices[0].template.template_path == (mine / "Mine.svg").resolve()
