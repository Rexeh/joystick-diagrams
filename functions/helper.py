import pprint
import os
from os import path
import webbrowser
from shutil import copyfile
import re
import config

pp = pprint.PrettyPrinter(indent=4)
webbrowser.register('chrome', None,webbrowser.BackgroundBrowser(config.chrome_path))
tempFilesDirectory = './temp/'
diagramFilesDirectory = './diagrams/'
templateFilesDirectory = './templates/'
fileSpacer = "_"

def updateDeviceArray(deviceArray, device, mode, buttons):    
    data = {"Buttons": buttons, "Axis": ""}
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
        log("Failed to create directory", directory, 1)
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
        svg = re.sub(regexSearch, v, svg)
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
    else:
        log("No template found for: ", device,3)

def log(text,item,level=1):
    #TODO - Tidy this thing up, output to proper file
    if(config.debugLevel==3 and level == 3):
        print(text)
        pp.pprint(item)
    if(config.debugLevel==2 and level == 3 or 2):
        print(text)
        pp.pprint(item)
    else:
        print(text)
        pp.pprint(item)

#TODO
# # https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth

# def nested_update(d, u):
#     for k, v in u.items():
#         if isinstance(v, collections.abc.Mapping):
#             d[k] = nested_update(d.get(k, {}), v)
#         else:
#             d[k] = v
#     return d

# def updateDeviceArray(deviceArray, device, mode, buttons):
#     data = {
#         device: {
#             mode: {
#               "Buttons": buttons,
#               "Axis": ""
#             }
#         }
#     }

#     nested_update(deviceArray, data)