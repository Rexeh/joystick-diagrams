import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from joystick_diagrams import app_init
from joystick_diagrams.utils import create_directory, data_root

log_path = Path.joinpath(data_root(), "logs")
create_directory(str(log_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(module)s %(filename)s - %(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            str(Path.joinpath(log_path, "application.log")),
            mode="a",
            maxBytes=5 * 1000000,
            backupCount=1,
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
