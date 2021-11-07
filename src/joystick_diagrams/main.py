import sys
import os
import logging
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore
from joystick_diagrams.ui import Ui_MainWindow
from joystick_diagrams import config, version

from joystick_diagrams.adaptors.dcs_world import DCSWorldParser
from joystick_diagrams.adaptors.joystick_gremlin import JoystickGremlin
from joystick_diagrams.adaptors.star_citizen import StarCitizen
from joystick_diagrams.classes import export
from joystick_diagrams.functions import helper

_logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.set_version()
        # Clean up GUI Defaults
        self.dcs_profiles_list.clear()
        self.jg_profile_list.clear()
        self.application_information_textbrowser.clear()
        # DCS UI Setup
        self.dcs_selected_directory_label.setText("")
        self.dcs_parser_instance = None
        self.jg_parser_instance = None
        self.dcs_directory = None
        self.jg_file = None
        self.jg_devices = None
        self.jg_modes = None
        self.dcs_easy_mode_checkbox.stateChanged.connect(self.easy_mode_checkbox_action)
        self.dcs_directory_select_button.clicked.connect(self.set_dcs_directory)
        self.export_button.clicked.connect(self.export_profiles)
        self.parser_selector.currentChanged.connect(self.change_export_button)
        self.change_export_button()
        self.donate_button.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(
                QtCore.QUrl(
                    "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=WLLDYGQM5Z39W&source=url"
                )
            )
        )
        self.discord_button.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://discord.gg/G8nRUS2"))
        )

        # JG UI Setup
        self.jg_select_profile_button.clicked.connect(self.set_jg_file)

        # SC UI Setup
        self.sc_file = None
        self.sc_parser_instance = None
        self.sc_select_button.clicked.connect(self.set_sc_file)

    def set_version(self) -> None:
        version_text = version.VERSION
        self.label_9.setText(version_text)
        self.setWindowTitle("Joystick Diagrams - V" + version_text)

    def change_export_button(self) -> None:
        if self.parser_selector.currentIndex() == 0:
            if self.jg_parser_instance:
                self.export_button.setEnabled(1)
            else:
                self.export_button.setDisabled(1)
        elif self.parser_selector.currentIndex() == 1:
            if self.dcs_parser_instance:
                self.export_button.setEnabled(1)
            else:
                self.export_button.setDisabled(1)
        elif self.parser_selector.currentIndex() == 2:
            if self.sc_parser_instance:
                self.export_button.setEnabled(1)
            else:
                self.export_button.setDisabled(1)
        else:
            self.export_button.setDisabled(1)

    def easy_mode_checkbox_action(self) -> None:
        if self.dcs_parser_instance:
            self.dcs_parser_instance.remove_easy_modes = self.dcs_easy_mode_checkbox.isChecked()
            self.dcs_profiles_list.clear()
            self.dcs_profiles_list.addItems(self.dcs_parser_instance.get_validated_profiles())

    def clear_info(self) -> None:
        self.application_information_textbrowser.clear()

    def enable_profile_load_button(self, button) -> None:
        button.setStyleSheet("background: #007acc; color: white;")

    def disable_profile_load_button(self, button) -> None:
        button.setStyleSheet("color:white; border: 1px solid white;")

    def print_to_info(self, error_text) -> None:
        self.application_information_textbrowser.append(error_text)
        self.application_information_textbrowser.verticalScrollBar().setValue(
            self.application_information_textbrowser.verticalScrollBar().maximum()
        )

    def set_dcs_directory(self):
        self.dcs_directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select DCS Saved Games Directory",
            os.path.expanduser("~/Saved Games/DCS"),
        )

        if self.dcs_directory:
            try:
                self.load_dcs_directory()
            except Exception as e:
                self.print_to_info("Error: {}".format(e))
        else:
            self.print_to_info("No DCS Directory Selected")

    def load_dcs_directory(self):
        try:
            self.dcs_profiles_list.clear()
            self.dcs_parser_instance = DCSWorldParser(
                self.dcs_directory, easy_modes=self.dcs_easy_mode_checkbox.isChecked()
            )
            self.print_to_info("Succesfully loaded DCS profiles")
            self.enable_profile_load_button(self.dcs_directory_select_button)
            self.dcs_selected_directory_label.setText("in {}".format(self.dcs_directory))
            self.export_button.setEnabled(1)
        except Exception:
            self.disable_profile_load_button(self.dcs_directory_select_button)
            self.export_button.setEnabled(0)
            self.dcs_selected_directory_label.setText("")
            raise
        else:
            self.dcs_profiles_list.clear()
            self.dcs_profiles_list.addItems(self.dcs_parser_instance.get_validated_profiles())

    def set_sc_file(self):
        self.clear_info()
        self.sc_file = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Star Citizen Config file", None, "XMl Files (*.xml)"
        )[0]
        if self.sc_file:
            self.load_sc_file()
        else:
            self.print_to_info("No File Selected")

    def load_sc_file(self) -> None:
        try:
            self.sc_parser_instance = StarCitizen(self.sc_file)
            self.enable_profile_load_button(self.sc_select_button)
            self.export_button.setEnabled(1)
            self.print_to_info("Succesfully loaded Star Citizen profile")
        except Exception as e:
            self.disable_profile_load_button(self.sc_select_button)
            self.export_button.setEnabled(0)
            self.sc_file = None
            self.print_to_info("Error Loading File: {}".format(e))

    def set_jg_file(self) -> None:
        self.jg_file = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Joystick Gremlin Config file",
            None,
            "Gremlin XMl Files (*.xml)",
        )[0]

        if self.jg_file:
            try:
                self.load_jg_file()
            except Exception as e:
                self.print_to_info("Error Loading File: {}".format(e))
        else:
            self.print_to_info("No File Selected")

    def load_jg_file(self):
        try:
            self.jg_parser_instance = JoystickGremlin(self.jg_file)
            self.jg_devices = self.jg_parser_instance.get_device_names()
            self.jg_modes = self.jg_parser_instance.get_modes()
            self.enable_profile_load_button(self.jg_select_profile_button)
            self.jg_profile_list.clear()
            self.jg_profile_list.addItems(self.jg_modes)
            self.export_button.setEnabled(1)
        except Exception as e:
            self.disable_profile_load_button(self.jg_select_profile_button)
            self.jg_profile_list.clear()
            self.export_button.setEnabled(0)
            raise e

    def export_profiles(self):
        if self.parser_selector.currentIndex() == 0:  ## JOYSTICK GREMLIN
            selected_profiles = self.jg_profile_list.selectedItems()
            if len(selected_profiles) > 0:
                profiles = []
                for item in selected_profiles:
                    profiles.append(item.text())
                self.print_to_info("Exporting the following profile(s): {}".format(profiles))
                data = self.jg_parser_instance.create_dictionary(profiles)
            else:
                data = self.jg_parser_instance.create_dictionary()
            self.export_to_svg(data, "JG")
        elif self.parser_selector.currentIndex() == 1:  ## DCS
            selected_profiles = self.dcs_profiles_list.selectedItems()
            if len(selected_profiles) > 0:
                profiles = []
                for item in selected_profiles:
                    profiles.append(item.text())
                self.print_to_info("Exporting the following profile(s): {}".format(profiles))
                data = self.dcs_parser_instance.process_profiles(profiles)
            else:
                data = self.dcs_parser_instance.process_profiles()
            self.export_to_svg(data, "DCS")
        elif self.parser_selector.currentIndex() == 2:  ## SC
            data = self.sc_parser_instance.parse()
            self.export_to_svg(data, "StarCitizen")
        else:
            pass  # no other tabs have functionality right now

    def export_to_svg(self, data, parser_type):

        self.export_progress_bar.setValue(0)
        self.clear_info()
        self.print_to_info("Export Started")
        exporter = export.Export(data, parser_type)
        success = exporter.export_config(self.export_progress_bar)
        for item in success:
            self.print_to_info(item)
        self.print_to_info("Export Finished")
        _logger.info(success)


def setup_logging() -> None:
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """

    log_dir = Path("logs")
    log_file = Path("jv.log")
    log_file_location = Path.joinpath(log_dir, log_file)

    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"

    if not Path.exists(log_dir):
        Path.mkdir(log_dir)

    logging.basicConfig(
        level=get_log_level(),
        filename=log_file_location,
        format=logformat,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_log_level() -> str:
    if config.debugLevel == 1:
        return "WARNING"
    if config.debugLevel == 2:
        return "ERROR"
    if config.debugLevel == 3:
        return "DEBUG"
    return "ERROR"


if __name__ == "__main__":

    setup_logging()

    try:
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.show()
        app.exec()
    except Exception as error:
        helper.log(error, "error", True)
