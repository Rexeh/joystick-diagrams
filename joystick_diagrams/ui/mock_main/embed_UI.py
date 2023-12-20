from PyQt5 import QtCore, QtGui, QtWidgets
from qt_material import apply_stylesheet

from joystick_diagrams.ui.mock_main.qt_designer import embed_ui


class EmbedWidget(QtWidgets.QWidget, embed_ui.Ui_Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = EmbedWidget()
    window.show()
    apply_stylesheet(app, theme="dark_lightgreen.xml")
    app.exec()
