import pytest
from PyQt5 import QtCore

import joystick_diagrams.__main__ as ui
import joystick_diagrams.classes.version.version as version


def test_title(qtbot):
    window = ui.MainWindow()
    qtbot.addWidget(window)
    title = "Joystick Diagrams - V"
    version_text = version.VERSION
    assert window.windowTitle() == f"{title}{version_text}"


def test_default_ui(qtbot):
    window = ui.MainWindow()
    window.show()
    qtbot.addWidget(window)
    assert not window.export_button.isEnabled()


@pytest.mark.skip(reason="No longer used in new UI")
def test_dcs_file_load_success(qtbot):
    window = ui.MainWindow()
    window.show()
    qtbot.addWidget(window)
    window.dcs_directory = "./tests/data/dcs_world/valid_dcs_world_directory"
    window.load_dcs_directory()
    assert window.dcs_profiles_list.count() == 2
    assert window.dcs_selected_directory_label.text() == "in ./tests/data/dcs_world/valid_dcs_world_directory"
    assert window.dcs_easy_mode_checkbox.isChecked()
    qtbot.mouseClick(window.dcs_easy_mode_checkbox, QtCore.Qt.LeftButton)
    assert window.dcs_profiles_list.count() == 3
    assert not window.dcs_easy_mode_checkbox.isChecked()


@pytest.mark.skip(reason="No longer used in new UI")
def test_dcs_file_load_failure_config(qtbot):
    window = ui.MainWindow()
    window.show()
    qtbot.addWidget(window)
    window.dcs_directory = "./tests/data/dcs_world/invalid_dcs_world_no_config"
    try:
        window.load_dcs_directory()
    except Exception as e:
        assert e.args[0] == "DCS: No Config Folder found in DCS Folder."


@pytest.mark.skip(reason="No longer used in new UI")
def test_dcs_file_load_failure_input(qtbot):
    window = ui.MainWindow()
    window.show()
    qtbot.addWidget(window)
    window.dcs_directory = "./tests/data/dcs_world/invalid_dcs_world_no_input"

    try:
        window.load_dcs_directory()
    except Exception as e:
        assert e.args[0] == "DCS: No input directory found"


def test_jg_file_load(qtbot):
    window = ui.MainWindow()
    window.show()
    qtbot.addWidget(window)
    assert window.jg_profile_list.count() == 0
    window.jg_file = "./tests/data/joystick_gremlin/gremlin_inherit_no_inherit.xml"
    window.load_jg_file()
    assert window.jg_profile_list.count() == 4


def test_sc_file_load_success(qtbot):
    window = ui.MainWindow()
    window.show()
    qtbot.addWidget(window)
    assert window.application_information_textbrowser.toPlainText() == ""
    window.sc_file = "./tests/data/star_citizen/layout_all_exported_valid.xml"
    window.load_sc_file()
    assert window.application_information_textbrowser.toPlainText() == "Succesfully loaded Star Citizen profile"


def test_sc_file_load_failure(qtbot):
    window = ui.MainWindow()
    window.show()
    qtbot.addWidget(window)
    assert window.application_information_textbrowser.toPlainText() == ""
    window.sc_file = "./tests/data/star_citizen/invalid.xml"
    window.load_sc_file()
    assert (
        window.application_information_textbrowser.toPlainText()
        == "Error Loading File: File is not a valid Star Citizen XML"
    )
