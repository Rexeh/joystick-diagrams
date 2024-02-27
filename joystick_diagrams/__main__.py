import logging

from joystick_diagrams import app_init

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
        app_init.init()

    except Exception as error:  # pylint: disable=broad-except
        _logger.exception(error)
