import pprint
import os
from os import path
import webbrowser
from shutil import copyfile
import re
import config

pp = pprint.PrettyPrinter(indent=4)
webbrowser.register('chrome', None,webbrowser.BackgroundBrowser(config.chrome_path))
tempDirectory = './temp/'

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

def createTemp():
    os.makedirs(tempDirectory)

def getTempPath(device, mode):
    tempPath = tempDirectory + device + "_" + mode + ".svg"
    
    if not os.path.exists(tempDirectory):
        createTemp()

    return tempPath

def findTemplate(device, temp):
    if path.exists("./templates/" + device + ".svg"):
        copyfile("./templates/" + device + ".svg", temp)
        return True
    else:
        return False

def saveDiagram(device, mode, stream):
    outputPath = "./diagrams/" + device + "_" + mode + ".svg"
    outputfile = open(outputPath, "w")
    outputfile.write(stream)
    return outputPath

def strReplaceSVG(devicelist,device,mode,stream):
    SVG_Input = stream
    for b, v in devicelist[device][mode]['Buttons'].items():
        regexSearch = "\\b" + b + "\\b"
        SVG_Input = re.sub(regexSearch, v, SVG_Input)
    return SVG_Input

def exportDevice(devicelist, device, mode):
    tempPath = getTempPath(device,mode)

    if findTemplate(device,tempPath):
        if config.export:
            with open(tempPath,'r') as file:
                SVG_Input = file.read()
            SVG_Input = strReplaceSVG(devicelist,device,mode,SVG_Input)
            title = "Profile Name: " + mode
            SVG_Input = re.sub("\\bTEMPLATE_NAME\\b", title, SVG_Input)
            outputPath = saveDiagram(device,mode,SVG_Input)
            if config.openinbrowser:
                webbrowser.get('chrome').open_new_tab(outputPath)
    else:
        log("No template found for: ", device,3)

def log(text,item,level=2):

    ##LOG LEVEL
    # 1 Debug
    # 2 Info

    if(config.debug):
        if config.debugLevel == 2 and level == 1:
            pass
        else:
            print(text)
            pp.pprint(item)
            print("----------------------------------------------------------------")

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