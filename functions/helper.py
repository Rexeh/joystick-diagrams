import pprint
import config
from os import path
import webbrowser
from shutil import copyfile
import re

pp = pprint.PrettyPrinter(indent=4)
webbrowser.register('chrome', None,webbrowser.BackgroundBrowser(config.chrome_path))

def updateDeviceArray(deviceArray, device, mode, buttons):
    
    data = {"Buttons": buttons, "Axis": ""}
    if config.debug:
        print("STARTING ARRAY IN HELPER")
        pp.pprint(deviceArray)

    if device in deviceArray:
        if config.debug:
            print("DEVICE FOUND IN ARRAY")
            print(deviceArray[device])

        if mode in deviceArray[device]:
            if config.debug:
                print("MODE FOR DEVICE FOUND IN ARRAY")
            deviceArray[device][mode].update(data)
        else:
            if config.debug:
                print("ADD MODE FOR DEVICE FOUND IN ARRAY")
            deviceArray[device].update({
                    mode:   data
                        })
    else:
        deviceArray.update({
            device : {
                mode:   data
                            }
        })

    if config.debug:
        print("EXITING ARRAY IN HELPER")
        pp.pprint(deviceArray)


def exportDevice(devicelist, device, mode):
    tempPath = "./temp/" + device + "_" + mode + ".svg"

    if path.exists("./templates/" + device + ".svg"):
        copyfile("./templates/" + device + ".svg", tempPath)
        
        if config.export:

            with open(tempPath,'r') as file:
                SVG_Input = file.read()

            for b, v in devicelist[device][mode]['Buttons'].items():
                regexSearch = "\\b" + b + "\\b"
                SVG_Input = re.sub(regexSearch, v, SVG_Input)

            title = "Profile Name: " + mode
            SVG_Input = re.sub("\\bTEMPLATE_NAME\\b", title, SVG_Input)

            outputPath = "./diagrams/" + device + "_" + mode + ".svg"
            outputfile = open(outputPath, "w")
            outputfile.write(SVG_Input)
        
            if config.openinbrowser:
                webbrowser.get('chrome').open_new_tab(outputPath)

def log(text,item):
    if(config.debug):
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