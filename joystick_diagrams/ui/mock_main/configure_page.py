import logging
import sys

from PySide6.QtCore import QDir, QMetaMethod, QObject, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QListWidgetItem, QMainWindow
from qt_material import apply_stylesheet

from joystick_diagrams import app_init
from joystick_diagrams.app_state import appState
from joystick_diagrams.ui.mock_main import parent_profiles
from joystick_diagrams.ui.mock_main.qt_designer import configure_page_ui

_logger = logging.getLogger(__name__)
5


class configurePage(QMainWindow, configure_page_ui.Ui_Form):  # Refactor pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = appState()
        self.treeWidget.header().setVisible(True)
        self.initialise_available_profiles()
        self.profileParentWidget = parent_profiles.parent_profile_ui()
        self.verticalLayout_6.addWidget(self.profileParentWidget)
        self.profileList.clicked.connect(self.handle_clicked_profile)
        self.profileToParentMapping = {}

    def get_profiles(self):
        return self.appState.profileObjectMapping

    def initialise_available_profiles(self):
        self.profileList.clear()
        profiles = self.get_profiles()
        for i in profiles.values():
            self.profileList.addItem(i.name)

    @Slot()
    def handle_clicked_profile(self, item):
        value = self.profileList.currentItem().text()
        self.profileParentWidget.set_profile_parent_map(value)


if __name__ == "__main__":
    logger = logging.basicConfig
    app = QApplication(sys.argv)
    app_init
    window = configurePage()
    window.show()
    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False)
    app.exec()
