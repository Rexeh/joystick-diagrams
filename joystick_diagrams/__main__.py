import logging
from logging.handlers import RotatingFileHandler

from joystick_diagrams import app_init

logging.basicConfig(
    level=logging.INFO,
    format="%(module)s %(filename)s - %(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            "application.log", mode="a", maxBytes=5 * 1000000, backupCount=1
        ),
    ],
)
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

if __name__ == "__main__":
    try:
        app_init.init()

    except Exception as error:
        _logger.exception(error)
