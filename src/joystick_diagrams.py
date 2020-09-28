import sys
import os
from PyQt5 import QtWidgets, uic, QtGui
from Ui import Ui_MainWindow
import adaptors.dcs_world as dcs
import adaptors.joystick_gremlin as jg
import functions.helper as helper
import version

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, obj=None, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setVersion()
        # Clean up GUI Defaults
        self.dcs_profiles_list.clear()
        self.jg_profile_list.clear()
        self.application_information_textbrowser.clear()
        # DCS UI Setup
        self.dcs_selected_directory_label.setText('')
        self.dcs_parser_instance = None
        self.jg_parser_instance = None
        self.dcs_easy_mode_checkbox.stateChanged.connect(self.easy_mode_checkbox_action)
        self.dcs_directory_select_button.clicked.connect(self.set_dcs_directory)
        self.export_button.clicked.connect(self.export_profiles)
        self.parser_selector.currentChanged.connect(self.change_export_button)
        self.change_export_button()

        # JG UI Setup
        self.jg_select_profile_button.clicked.connect(self.set_jg_file)

    def setVersion(self):
        version_text = version.VERSION
        self.setWindowTitle("Joystick Diagrams - V" + version_text)

    def change_export_button(self):
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
        else:
            self.export_button.setDisabled(1)

    def easy_mode_checkbox_action(self):
        if self.dcs_parser_instance:
            self.dcs_parser_instance.remove_easy_modes = self.dcs_easy_mode_checkbox.isChecked()
            self.dcs_profiles_list.clear()
            self.dcs_profiles_list.addItems(self.dcs_parser_instance.getValidatedProfiles())

    def print_to_info(self, error):
        self.application_information_textbrowser.append(error)
        self.application_information_textbrowser.verticalScrollBar().setValue(self.application_information_textbrowser.verticalScrollBar().maximum())

    def set_dcs_directory(self):
        self.dcs_directory = QtWidgets.QFileDialog.getExistingDirectory(self,"Select DCS Saved Games Directory",os.path.expanduser("~"))
        if self.dcs_directory:
            self.load_dcs_directory()
        else:
            pass

    def load_dcs_directory(self):
        try:
            self.dcs_profiles_list.clear()
            self.dcs_parser_instance = dcs.DCSWorld_Parser(self.dcs_directory,easy_modes=self.dcs_easy_mode_checkbox.isChecked())
            self.print_to_info('Succesfully loaded DCS profiles')
            self.dcs_directory_select_button.setStyleSheet('background: #007acc; color: white;')
            self.dcs_selected_directory_label.setText('in {}'.format(self.dcs_directory))
            self.export_button.setEnabled(1)
        except Exception as error:
            self.print_to_info(error.args[0])
        else:
            self.dcs_profiles_list.clear()
            self.dcs_profiles_list.addItems(self.dcs_parser_instance.getValidatedProfiles())

    def set_jg_file(self):
        self.jg_file = QtWidgets.QFileDialog.getOpenFileName(self,"Select Joystick Gremlin Config file",None,"Gremlin XMl Files (*.xml)")[0]
        try:
            self.load_jg_file()
        except:
            print("Error Loading JG File")
        else:
            pass

    def load_jg_file(self):
        try:
            self.jg_parser_instance = jg.JoystickGremlin(self.jg_file)
            self.jg_devices = self.jg_parser_instance.get_device_names()
            self.jg_modes = self.jg_parser_instance.get_modes()
            self.jg_select_profile_button.setStyleSheet('background: #007acc; color: white;')
            self.jg_profile_list.clear()
            self.jg_profile_list.addItems(self.jg_modes)
            self.export_button.setEnabled(1)
        except:
            print("Ooops problem with JG file")
        else:
            pass

    def export_profiles(self):
        if self.parser_selector.currentIndex() == 0: ## JOYSTICK GREMLIN
            selected_profiles = self.jg_profile_list.selectedItems()
            if len(selected_profiles)>0:
                profiles = []
                for item in selected_profiles:
                    profiles.append(item.text())
                self.print_to_info("Exporting the following profile(s): {}".format(profiles))
                data = self.jg_parser_instance.createDictionary(profiles)
            else:
                data = self.jg_parser_instance.createDictionary()
            self.export_to_svg(data, 'JG')
        elif self.parser_selector.currentIndex() == 1:  ## DCS
            selected_profiles = self.dcs_profiles_list.selectedItems()
            if len(selected_profiles)>0:
                profiles = []
                for item in selected_profiles:
                    profiles.append(item.text())
                self.print_to_info("Exporting the following profile(s): {}".format(profiles))
                data = self.dcs_parser_instance.processProfiles(profiles)
            else:
                data = self.dcs_parser_instance.processProfiles()
            self.export_to_svg(data, 'DCS')
        else:
            pass # no other tabs have functionality right now

    def export_to_svg(self, data,parser_type):

        self.export_progress_bar.setValue(0)
        data = data
        type = parser_type
        joycount = len(data)
        run_state = []

        for joystick in data:
            print(joystick)
            for mode in data[joystick]:
                success = helper.exportDevice(type, data, joystick, mode)
                helper.log(success, 'debug')
                # Log failures
                if success[0] == False and success[1] not in run_state:
                    helper.log("Device: {} does not have a valid template".format(success[1]), 'debug')
                    run_state.append(success[1])
            self.export_progress_bar.setValue(self.export_progress_bar.value() + int(100/joycount))
        if(len(run_state)>0):
            errorText = "The following devices did not have matching templates in /templates. \n\n Device names must match the template name exactly.\n"
            for item in run_state:
                errorText = errorText+'\n'+item
            errorText = errorText+'\n\n'+"No diagrams have been created for the above"
            helper.log(errorText, 'warning')
            self.print_to_info(errorText)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
