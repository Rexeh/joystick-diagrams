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
logDir = './logs/'
logFile = 'jv.log'   
logger = logging.getLogger('jv')
webbrowser.register('chrome', None,webbrowser.BackgroundBrowser(config.chrome_path))
        
def log(text, level='info'):
    #Accepted Levels
    # info, warning, error
    if config.debug:
        if level == 'info':
            logger.info(text)
        elif level == 'warning':
            logger.warning(text)
        elif level == 'error':
            logger.error(text)
        else:
            logger.debug(text)
        

def getVersion():
    return "Version: " + version.VERSION

if not os.path.exists(logDir):
    createDirectory(logDir)
hdlr = logging.FileHandler(logDir + logFile)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
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