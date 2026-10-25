"""4. Diagrams › Layout: every layout read and write carries the controller's guid."""
# ruff: noqa: F811 (pytest fixtures imported from tests/ui/stage34_fixtures.py)

import os
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.db.layout_service import LayoutService  # noqa: E402
from joystick_diagrams.render.layout import TEMPLATE_LAYER, MoveOp  # noqa: E402
from joystick_diagrams.ui.customise_layout import CustomiseLayout  # noqa: E402
from joystick_diagrams.ui.layout_editor.session import LayoutEditSession  # noqa: E402
from tests.ui.stage34_fixtures import (  # noqa: E402, F401
    PANEL,
    STARTER_KEY,
    STICK,
    THROTTLE,
    _reset_app_state,
    seed_state,
    settings_store,
)


class SpyService:
    """Wraps a real LayoutService and records the device_guid of every call."""

    def __init__(self, real: LayoutService):
        self.real = real
        self.calls: list[tuple[str, str | None]] = []

    def __getattr__(self, name):
        target = getattr(self.real, name)
        if not callable(target):
            return target

        def wrapper(*args, **kwargs):
            guid = kwargs.get("device_guid")
            if guid is None and name in ("get_document",) and len(args) >= 3:
                guid = args[2]
            if guid is None and name == "layers_of_template" and len(args) >= 2:
                guid = args[1]
            self.calls.append((name, guid))
            return target(*args, **kwargs)

        return wrapper


@pytest.fixture
def screen(qapp, settings_store):
    state = seed_state()
    spy = SpyService(state.layout_service)
    screen = CustomiseLayout()
    screen.service = spy
    screen.refresh()
    yield screen, spy
    screen.shutdown()


@pytest.mark.uitest
def test_session_writes_are_keyed_by_controller(screen):
    page, spy = screen
    page.show_device(STICK)
    assert page._session.device_guid == STICK
    spy.calls.clear()
    page._session.move("button_1", 5, 0)
    page._session.hide("button_2")
    page._session.undo()
    page._session.reset_all()
    assert spy.calls, "the session used the layout service"
    assert all(guid in (STICK, "") for _name, guid in spy.calls), spy.calls
    writes = [c for c in spy.calls if c[0] in ("set_ops", "append_op", "clear")]
    assert writes and all(guid in (STICK, "") for _n, guid in writes)
    assert any(guid == STICK for _n, guid in writes)


@pytest.mark.uitest
def test_two_controllers_on_one_template_keep_independent_layouts(screen):
    page, _spy = screen
    page.show_device(STICK)
    page._session.move("button_1", 5, 0)
    real = page.service.real
    assert len(real.get_document(STARTER_KEY, TEMPLATE_LAYER, STICK).ops) == 1
    assert real.get_document(STARTER_KEY, TEMPLATE_LAYER, THROTTLE).ops == []
    page.show_device(THROTTLE)
    assert page._session.device_guid == THROTTLE
    assert page._session.layers().is_empty


@pytest.mark.uitest
def test_shared_rows_are_read_until_the_controller_edits(qapp, settings_store):
    service = LayoutService()
    service.set_ops(
        STARTER_KEY, TEMPLATE_LAYER, [MoveOp(target="button_1", dx=1)], None
    )
    session = LayoutEditSession(service, STARTER_KEY, None, device_guid=STICK)
    assert len(session.ops_in(TEMPLATE_LAYER)) == 1  # falls back to the shared row
    session.move("button_2", 2, 0)
    own = service.get_document(STARTER_KEY, TEMPLATE_LAYER, STICK).ops
    assert [op.target.split("#")[0] for op in own] == ["button_1", "button_2"]


@pytest.mark.uitest
def test_save_as_template_bakes_this_controllers_layout(screen):
    from joystick_diagrams.ui.layout_save_template_dialog import SaveTemplateDialog

    page, _spy = screen
    page.show_device(STICK)
    page._session.move("button_1", 5, 0)
    entry = page.current_diagram()
    dialog = SaveTemplateDialog(
        template=entry.template,
        session=page._session,
        export_device=page._export_device,
        device_name=entry.device_name,
        device_id=entry.device_id,
        theme=None,
    )
    layers = dialog.layers_to_bake()
    assert layers.template.device_guid == STICK
    assert len(layers.template.ops) == 1


@pytest.mark.uitest
def test_picker_lists_controllers_needing_a_template_and_pages(qapp, settings_store):
    state = seed_state()
    state.page_service.create("Stick + Throttle", [STICK, THROTTLE])
    page = CustomiseLayout()
    page.refresh()
    texts = [page.diagram_combo.itemText(i) for i in range(page.diagram_combo.count())]
    assert texts[0].startswith("Gladiator NXT")
    assert "Button Box · needs a template · Choose template…" in texts
    assert texts[-1] == "▣ Stick + Throttle"
    page.show_device(PANEL)
    assert page.canvas_stack.currentWidget() is page.needs_state
    assert not page.add_box_button.isEnabled()
    page.show_page(state.page_service.pages()[0].page_id)
    assert page.canvas_stack.currentWidget() is page.page_host
    svg = page.render_page_synchronously()
    assert svg and svg.lstrip().startswith("<")
    page.shutdown()


@pytest.mark.uitest
def test_choose_template_in_place(qapp, settings_store, monkeypatch, tmp_path):
    from tests.ui.stage34_fixtures import STARTER_TEMPLATE

    seed_state()
    page = CustomiseLayout()
    page.refresh()
    page.show_device(PANEL)
    chooser = MagicMock(return_value=True)

    def choose(parent, guid, name):
        from joystick_diagrams.app_state import AppState

        AppState().device_service.set_template(guid, str(STARTER_TEMPLATE))
        return chooser(guid, name)

    monkeypatch.setattr("joystick_diagrams.ui.export_page.choose_template_for", choose)
    page.choose_template_for_selected()
    chooser.assert_called_once_with(PANEL, "Button Box")
    assert page.current_diagram() is not None
    assert page.current_diagram().device_id == PANEL
    page.shutdown()
