import pytest
import pytestqt
from PyQt5 import QtCore, QtWidgets
import joystick_diagrams
import version

def test_title(qtbot):

    window = joystick_diagrams.MainWindow()
    qtbot.addWidget(window)

    title = "Joystick Diagrams - V"
    version_text = version.VERSION
    assert window.windowTitle() == "{title}{version}".format(title=title,version=version_text)

def test_default_ui(qtbot):

    window = joystick_diagrams.MainWindow()
    window.show()
    qtbot.addWidget(window)
    
    assert(window.export_button.isEnabled() == False)

def test_dcs_file_load_success(qtbot):

    window = joystick_diagrams.MainWindow()
    window.show()
    qtbot.addWidget(window)
    
    window.dcs_directory = './tests/data/dcs_world/valid_dcs_world_directory'
    window.load_dcs_directory()

    assert(window.dcs_profiles_list.count() == 2)
    assert(window.dcs_selected_directory_label.text() == 'in ./tests/data/dcs_world/valid_dcs_world_directory')

    assert(window.dcs_easy_mode_checkbox.isChecked() == True)
    
    qtbot.mouseClick(window.dcs_easy_mode_checkbox, QtCore.Qt.LeftButton)

    assert(window.dcs_profiles_list.count() == 3)
    assert(window.dcs_easy_mode_checkbox.isChecked() == False)

def test_dcs_file_load_failure_config(qtbot):

    window = joystick_diagrams.MainWindow()
    window.show()
    qtbot.addWidget(window)
    
    window.dcs_directory = './tests/data/dcs_world/invalid_dcs_world_no_config'
    window.load_dcs_directory()
    assert(window.application_information_textbrowser.toPlainText() == 'DCS: No Config Folder found in DCS Folder.')

def test_dcs_file_load_failure_input(qtbot):

    window = joystick_diagrams.MainWindow()
    window.show()
    qtbot.addWidget(window)
    
    window.dcs_directory = './tests/data/dcs_world/invalid_dcs_world_no_input'
    window.load_dcs_directory()
    assert(window.application_information_textbrowser.toPlainText() == 'DCS: No input directory found')

def test_jg_file_load(qtbot):

    window = joystick_diagrams.MainWindow()
    window.show()
    qtbot.addWidget(window)

    assert(window.jg_profile_list.count() == 0)
    
    window.jg_file = './tests/data/joystick_gremlin/gremlin_inherit_no_inherit.xml'
    window.load_jg_file()

    assert(window.jg_profile_list.count() == 4)
 