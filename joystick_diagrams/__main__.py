import logging
import sys

from PySide6 import QtWidgets
from qt_material import apply_stylesheet

from joystick_diagrams import app_init

# from joystick_diagrams.ui.main_window.main_window import MainWindow
from joystick_diagrams.ui.mock_main.mock_main import MainWindow

logging.basicConfig(
    level=logging.DEBUG,
    format="%(module)s %(filename)s - %(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("application.log", mode="a"),
    ],
)
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)


if __name__ == "__main__":
    try:
        # Initiate pre-loading
        init = app_init.init()

        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.show()

        extra = {
            # Button colors
            "danger": "#dc3545",
            "warning": "#ffc107",
            "success": "#27ae60",
            # Font
            "font_family": "Roboto",
        }

        apply_stylesheet(
            app, theme="dark_blue.xml", invert_secondary=False, extra=extra
        )

        app.exec()
    except Exception as error:  # pylint: disable=broad-except
        _logger.exception(error)
