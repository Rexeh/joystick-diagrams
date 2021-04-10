import os
from os import path
import webbrowser
from shutil import copyfile
import re
import config
import version
import logging
import html

# Logging Init
LOG_DIR = "./logs/"
LOG_FILE = "jv.log"
logger = logging.getLogger("jv")
webbrowser.register("chrome", None, webbrowser.BackgroundBrowser(config.chrome_path))


def create_directory(directory):
    if not os.path.exists(directory):
        return os.makedirs(directory)
    else:
        log("Failed to create directory: {}".format(directory), "error")
        return False


def log(text, level="info", exc_info=False):
    # Accepted Levels
    # info, warning, error
    if config.debug:
        if level == "info":
            logger.info(text, exc_info=False)
        elif level == "warning":
            logger.warning(text, exc_info=False)
        elif level == "error":
            logger.error(text, exc_info=True)
        else:
            logger.debug(text, exc_info=True)


def getVersion():
    return "Version: " + version.VERSION


if not os.path.exists(LOG_DIR):
    create_directory(LOG_DIR)
hdlr = logging.FileHandler(LOG_DIR + LOG_FILE)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
if config.debugLevel == 1:
    logger.setLevel(logging.WARNING)
elif config.debugLevel == 2:
    logger.setLevel(logging.ERROR)
elif config.debugLevel == 3:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.WARNING)
