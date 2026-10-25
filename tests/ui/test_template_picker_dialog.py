"""TemplatePickerDialog: maker tree, fit counts, search, starter copy, the file
escape hatch, Remove template and the ``pick_template`` compatibility path."""

import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QDialog  # noqa: E402

from joystick_diagrams import template_catalog  # noqa: E402
from joystick_diagrams.ui import template_picker  # noqa: E402
from joystick_diagrams.ui.template_picker import (  # noqa: E402
    ROLE_KIND,
    TemplatePickerDialog,
    pick_template,
)
from joystick_diagrams.utils import user_templates_root  # noqa: E402
from tests.ui.stage_fixtures import (  # noqa: E402
    STICK,
    TEST_TEMPLATE,
    FakeProfileWrapper,
    drain,
    patched_settings,
    profile_with,
    seed_app_state,
)

FIT_TEXT = re.compile(
    r"^(Has all \d+ controls you use|\d+ of \d+ controls fit|No bindings to check)$"
)


@pytest.fixture(autouse=True)
def _fresh_state(temp_database):
    with patched_settings():
        seed_app_state(profile_wrappers=[FakeProfileWrapper(profile_with("F-16C"))])
        yield
    drain()
    from joystick_diagrams.app_state import AppState

    AppState._inst = None


@pytest.fixture
def dialog(qtbot):
    widget = TemplatePickerDialog(STICK)
    qtbot.addWidget(widget)
    assert widget.wait_for_fits()
    return widget


def top_level_labels(dialog):
    return [
        dialog.tree.topLevelItem(i).text(0)
        for i in range(dialog.tree.topLevelItemCount())
    ]


def test_title_names_the_controller_and_sort_by_fit_is_off(dialog):
    assert dialog.windowTitle() == 'Choose a template for "Gladiator NXT"'
    assert not dialog.sort_by_fit.isChecked()
    assert dialog.search.placeholderText() == "Search"
    assert not dialog.use_button.isEnabled()  # nothing pre-selected


def test_makers_then_my_templates(dialog):
    labels = top_level_labels(dialog)
    assert labels[0] == "All templates by maker"
    assert labels[-1] == "My templates"
    makers = template_catalog.makers(template_catalog.bundled_templates())
    assert labels[1:-1] == makers
    starter = template_catalog.starter_template()
    assert starter.key not in dialog._items  # offered once, under Can't find yours?


def test_every_template_row_has_a_fit_count(dialog):
    items = dialog.template_items()
    assert items
    for item in items:
        assert FIT_TEXT.match(item.text(1)), item.text(1)
    # the stick binds button 1 only: most templates have it
    assert any(item.text(1) == "Has all 1 controls you use" for item in items)


def test_search_by_name_or_maker(dialog):
    dialog.search.setText("warthog")
    names = [item.text(0) for item in dialog.template_items()]
    assert names and all("warthog" in n.lower() for n in names)
    dialog.search.setText("virpil")
    infos = [
        item.data(0, template_picker.ROLE_INFO) for item in dialog.template_items()
    ]
    assert infos and all(i.maker.lower() == "virpil" for i in infos)
    dialog.search.setText("zzzz-nothing")
    assert dialog.template_items() == []
    assert dialog.no_results.text() == 'No templates match "zzzz-nothing"'


def test_sort_by_fit_flattens_the_list(dialog):
    dialog.sort_by_fit.setChecked(True)
    kinds = {
        dialog.tree.topLevelItem(i).data(0, ROLE_KIND)
        for i in range(dialog.tree.topLevelItemCount())
    }
    assert kinds == {"template"}


def test_preview_pane_and_missing_controls(dialog, qtbot):
    info = next(i for i in template_catalog.bundled_templates() if not i.is_starter)
    dialog.select_template(info.key)
    assert dialog.preview_name.text() == info.name
    assert dialog.preview_source.text().endswith("Included with the app")
    assert dialog.use_button.isEnabled()
    drain()
    assert dialog.thumbnail.pixmap() is not None
    # fabricate a partial fit to check the expandable list
    from joystick_diagrams.template_catalog import FitResult

    dialog._fits[info.key] = FitResult(3, ("Button 31", "Hat 3 Up"), False)
    dialog._show_fit(info)
    assert dialog.preview_fit.text() == "1 of 3 controls you use are on this template."
    assert dialog.missing_toggle.text() == "2 controls missing"
    dialog.missing_toggle.click()
    assert dialog.missing_list.isVisibleTo(dialog)
    assert dialog.missing_list.text() == "Button 31, Hat 3 Up"


def test_use_this_template_assigns_it(dialog):
    from joystick_diagrams.app_state import AppState

    info = next(i for i in template_catalog.bundled_templates() if not i.is_starter)
    dialog.select_template(info.key)
    dialog.use_button.click()
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_value.path == info.path
    assert Path(AppState().device_service.template(STICK).path) == info.path


def test_starter_template_is_copied_named_and_assigned(dialog):
    from joystick_diagrams.app_state import AppState

    dialog.starter_button.click()
    result = dialog.result_value
    assert result.created_from_starter
    assert result.path.parent == user_templates_root()
    assert result.path.name == "Gladiator NXT.svg"
    assert Path(AppState().device_service.template(STICK).path) == result.path


def test_a_file_from_this_computer(dialog):
    from joystick_diagrams.app_state import AppState

    accepted = template_picker.QFileDialog.DialogCode.Accepted
    file_dialog = MagicMock()
    file_dialog.exec.return_value = accepted
    file_dialog.selectedFiles.return_value = [str(TEST_TEMPLATE)]
    with patch.object(template_picker, "QFileDialog") as cls:
        cls.return_value = file_dialog
        cls.DialogCode.Accepted = accepted
        dialog.file_link.click()
    assert dialog.result_value.path == TEST_TEMPLATE
    assert Path(AppState().device_service.template(STICK).path) == TEST_TEMPLATE


def test_remove_template_only_when_one_is_set(qtbot):
    from joystick_diagrams.app_state import AppState

    service = AppState().device_service
    first = TemplatePickerDialog(STICK)
    qtbot.addWidget(first)
    assert first.remove_button.isHidden()
    service.set_template(STICK, TEST_TEMPLATE)
    second = TemplatePickerDialog(STICK)
    qtbot.addWidget(second)
    assert not second.remove_button.isHidden()
    second.remove_button.click()
    assert second.result_value.removed
    assert service.template(STICK) is None
    drain()


def test_pick_template_returns_the_path_without_assigning(qtbot):
    from joystick_diagrams.app_state import AppState

    info = next(i for i in template_catalog.bundled_templates() if not i.is_starter)

    def fake_exec(self):
        self.select_template(info.key)
        self._use_selected()
        return QDialog.DialogCode.Accepted

    with patch.object(TemplatePickerDialog, "exec", fake_exec):
        path = pick_template(None, "Choose a template", device_guid=STICK)
    assert path == info.path
    assert AppState().device_service.template(STICK) is None
    drain()


def test_cancel_returns_nothing(qtbot):
    with patch.object(
        TemplatePickerDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    ):
        assert pick_template(None, "x") is None
    drain()
