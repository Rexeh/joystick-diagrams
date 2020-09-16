import os
from os import path
import webbrowser
from shutil import copyfile
import re
import config
import version
import logging

# Logging Init
logDir = './logs/'
logFile = 'jv.log'   
logger = logging.getLogger('jv')
webbrowser.register('chrome', None,webbrowser.BackgroundBrowser(config.chrome_path))
tempFilesDirectory = './temp/'
diagramFilesDirectory = './diagrams/'
templateFilesDirectory = './templates/'
fileSpacer = "_"

def updateDeviceArray(deviceArray, device, mode, inherit, buttons):
    data = {
        "Buttons": buttons,
        "Axis": "",
        "Inherit": inherit}

    if device in deviceArray:
        if mode in deviceArray[device]:
            deviceArray[device][mode].update(data)
        else:
            deviceArray[device].update({
                    mode:   data
                        })
    else:
        deviceArray.update({
            device : {
                mode:   data
                            }
        })

def createDirectory(directory):
    if not os.path.exists(directory):
        return os.makedirs(directory)
    else:
        log("Failed to create directory: {}".format(directory), 'error')
        return False

def getTempPath(device, mode):
    temporaryTemplateFile = tempFilesDirectory + device + "_" + mode + ".svg"
    if not os.path.exists(tempFilesDirectory):
        createDirectory(tempFilesDirectory)
    return temporaryTemplateFile

def findTemplate(device, templatePath):
    if path.exists(templateFilesDirectory + device + ".svg"):
        copyfile(templateFilesDirectory + device + ".svg", templatePath)
        return True
    else:
        return False

def saveDiagram(device, mode, stream):
    outputPath = diagramFilesDirectory + device + "_" + mode + ".svg"
    if not os.path.exists(diagramFilesDirectory):
        createDirectory(diagramFilesDirectory)
    outputfile = open(outputPath, "w")
    outputfile.write(stream)
    return outputPath

def strReplaceSVG(devicelist,device,mode,svg):
    for b, v in devicelist[device][mode]['Buttons'].items():
        regexSearch = "\\b" + b + "\\b"
        svg = re.sub(regexSearch, v, svg, flags=re.IGNORECASE)
    return svg

def addTemplateNameToSVG(title,svg):
    svg = re.sub("\\bTEMPLATE_NAME\\b", title, svg)
    return svg

def exportDevice(devicelist, device, mode):
    temporaryTemplateFile = getTempPath(device,mode)
    if findTemplate(device,temporaryTemplateFile):
        if config.export:
            with open(temporaryTemplateFile,'r') as file:
                svg = file.read()
            svg = strReplaceSVG(devicelist,device,mode,svg)
            title = "Profile Name: " + mode
            svg = re.sub("\\bTEMPLATE_NAME\\b", title, svg)
            outputPath = saveDiagram(device,mode,svg)
            if config.openinbrowser:
                webbrowser.get('chrome').open_new_tab(outputPath)
        return (True, device)
    else:
        log("No template found for: {}".format(device), 'debug')
        return (False, device)
        
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