from PyQt5 import QtCore

import joystick_diagrams.classes.version.version as version
from joystick_diagrams.ui.main_window import main_window


def test_title(qtbot):
    window = main_window.MainWindow()
    qtbot.addWidget(window)
    title = "Joystick Diagrams - V"
    version_text = version.VERSION
    assert window.windowTitle() == f"{title}{version_text}"


def test_default_main_window(qtbot):
    window = main_window.MainWindow()
    window.show()
    qtbot.addWidget(window)
    assert not window.export_button.isEnabled()


def test_jg_file_load(qtbot):
    window = main_window.MainWindow()
    window.show()
    qtbot.addWidget(window)
    assert window.jg_profile_list.count() == 0
    window.jg_file = "./tests/data/joystick_gremlin/gremlin_inherit_no_inherit.xml"
    window.load_jg_file()
    assert window.jg_profile_list.count() == 4


def test_sc_file_load_success(qtbot):
    window = main_window.MainWindow()
    window.show()
    qtbot.addWidget(window)
    assert window.application_information_textbrowser.toPlainText() == ""
    window.sc_file = "./tests/data/star_citizen/layout_all_exported_valid.xml"
    window.load_sc_file()
    assert window.application_information_textbrowser.toPlainText() == "Succesfully loaded Star Citizen profile"


def test_sc_file_load_failure(qtbot):
    window = main_window.MainWindow()
    window.show()
    qtbot.addWidget(window)
    assert window.application_information_textbrowser.toPlainText() == ""
    window.sc_file = "./tests/data/star_citizen/invalid.xml"
    window.load_sc_file()
    assert (
        window.application_information_textbrowser.toPlainText()
        == "Error Loading File: File is not a valid Star Citizen XML"
    )
