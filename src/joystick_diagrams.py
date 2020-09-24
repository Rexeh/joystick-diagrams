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
        self.dcs_easy_mode_checkbox.stateChanged.connect(self.easy_mode_checkbox_action)
        self.dcs_directory_select_button.clicked.connect(self.set_dcs_directory)
        self.export_button.clicked.connect(self.export_profiles)

        # JG UI Setup
        self.jg_select_profile_button.clicked.connect(self.set_jg_file)

    def setVersion(self):
        version_text = version.VERSION
        self.setWindowTitle("Joystick Diagrams - V" + version_text)

    def easy_mode_checkbox_action(self):
        if self.dcs_parser_instance:
            self.dcs_parser_instance.remove_easy_modes = self.dcs_easy_mode_checkbox.isChecked()
            self.dcs_profiles_list.clear()
            self.dcs_profiles_list.addItems(self.dcs_parser_instance.getValidatedProfiles())

    def print_to_info(self, error):
        self.application_information_textbrowser.append(error)
        self.application_information_textbrowser.verticalScrollBar().setValue(self.application_information_textbrowser.verticalScrollBar().maximum())
        #     scrollbar.setValue(scrollbar.maximum())

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
            self.dcs_directory_select_button.setStyleSheet('background: green; color: white;')
            self.dcs_selected_directory_label.setText('in {}'.format(self.dcs_directory))
        except Exception as error:
            self.print_to_info(error.args[0])
        else:
            self.dcs_profiles_list.clear()
            self.dcs_profiles_list.addItems(self.dcs_parser_instance.getValidatedProfiles())

    def set_jg_file(self):
        self.jg_file = QtWidgets.QFileDialog.getOpenFileName(self,"Select Joystick Gremlin Config file",None,"Gremlin XMl Files (*.xml)")[0]
        print(self.jg_file)
        try:
            self.jg_parser_instance = jg.JoystickGremlin(self.jg_file)
            print(self.jg_parser_instance)
        except:
            print("Ooops")
        else:
            pass

    def export_profiles(self):
 
        if self.parser_selector.currentIndex() == 0: ## JOYSTICK GREMLIN
            data = self.jg_parser_instance.createDictionary()

            runState = []
            self.export_progress_bar.setValue(0)
            joycount = len(data)
            for joystick in data:
                for mode in data[joystick]:
                    success = helper.exportDevice('JG', data, joystick, mode)
                    helper.log(success, 'debug')
                    # Log failures
                    if success[0] == False and success[1] not in runState:
                        helper.log("Device: {} does not have a valid template".format(success[1]), 'debug')
                        runState.append(success[1])
                self.export_progress_bar.setValue(self.export_progress_bar.value() + int(100/joycount))
            if(len(runState)>0):
                errorText = "The following devices did not have matching templates in /templates. \n\n Device names must match the template name exactly.\n"
                for item in runState:
                    errorText = errorText+'\n'+item
                errorText = errorText+'\n\n'+"No diagrams have been created for the above"
                helper.log(errorText, 'warning')
                self.print_to_info(errorText)

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

            runState = []
            self.export_progress_bar.setValue(0)
            joycount = len(data)
            for joystick in data:
                for mode in data[joystick]:
                    success = helper.exportDevice('DCS', data, joystick, mode)
                    helper.log(success, 'debug')
                    # Log failures
                    if success[0] == False and success[1] not in runState:
                        helper.log("Device: {} does not have a valid template".format(success[1]), 'debug')
                        runState.append(success[1])
                self.export_progress_bar.setValue(self.export_progress_bar.value() + int(100/joycount))
            if(len(runState)>0):
                errorText = "The following devices did not have matching templates in /templates. \n\n Device names must match the template name exactly.\n"
                for item in runState:
                    errorText = errorText+'\n'+item
                errorText = errorText+'\n\n'+"No diagrams have been created for the above"
                helper.log(errorText, 'warning')
                self.print_to_info(errorText)
        else:
            pass # no other tabs have functionality right now

'''
# TO DO
- DONE Hook up Joystick Gremlin
- DONE Make % thing work

- Make JG Filters choosable
- Fix strings in the output file to remove unsafe chars
- Hook up logs button?
- Hook up Settings? What's really going in here... DEBUG? Export to Browser?
- Add tests
'''

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
