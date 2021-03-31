from PyQt5 import QtCore
import pytest
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
    assert not window.export_button.isEnabled()

def test_dcs_file_load_success(qtbot):
    window = joystick_diagrams.MainWindow()
    window.show()
    qtbot.addWidget(window)
    window.dcs_directory = './tests/data/dcs_world/valid_dcs_world_directory'
    window.load_dcs_directory()
    assert window.dcs_profiles_list.count() == 2
    assert window.dcs_selected_directory_label.text() == 'in ./tests/data/dcs_world/valid_dcs_world_directory'
    assert window.dcs_easy_mode_checkbox.isChecked()
    qtbot.mouseClick(window.dcs_easy_mode_checkbox, QtCore.Qt.LeftButton)
    assert window.dcs_profiles_list.count() == 3
    assert not window.dcs_easy_mode_checkbox.isChecked()

def test_dcs_file_load_failure_config(qtbot):
    window = joystick_diagrams.MainWindow()
    window.show()
    qtbot.addWidget(window)
    window.dcs_directory = './tests/data/dcs_world/invalid_dcs_world_no_config'
    try:
        window.load_dcs_directory()
    except Exception as e:
        assert e.args[0] == 'DCS: No Config Folder found in DCS Folder.'

def test_dcs_file_load_failure_input(qtbot):
    window = joystick_diagrams.MainWindow()
    window.show()
    qtbot.addWidget(window)
    window.dcs_directory = './tests/data/dcs_world/invalid_dcs_world_no_input'
    
    try:
        window.load_dcs_directory()
    except Exception as e:
        assert e.args[0] == 'DCS: No input directory found'
        
    
def test_jg_file_load(qtbot):
    window = joystick_diagrams.MainWindow()
    window.show()
    qtbot.addWidget(window)
    assert window.jg_profile_list.count() == 0
    window.jg_file = './tests/data/joystick_gremlin/gremlin_inherit_no_inherit.xml'
    window.load_jg_file()
    assert window.jg_profile_list.count() == 4
 
def test_sc_file_load_success(qtbot):
    window = joystick_diagrams.MainWindow()
    window.show()
    qtbot.addWidget(window)
    assert window.application_information_textbrowser.toPlainText() == ''
    window.sc_file = './tests/data/star_citizen/valid.xml'
    window.load_sc_file()
    assert window.application_information_textbrowser.toPlainText() == 'Succesfully loaded Star Citizen profile'

def test_sc_file_load_failure(qtbot):
    window = joystick_diagrams.MainWindow()
    window.show()
    qtbot.addWidget(window)
    assert window.application_information_textbrowser.toPlainText() == ''
    window.sc_file = './tests/data/star_citizen/invalid.xml'
    window.load_sc_file()
    assert window.application_information_textbrowser.toPlainText() == 'Error Loading File: File is not a valid Starcraft Citizen XML'