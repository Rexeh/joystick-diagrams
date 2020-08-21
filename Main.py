from xml.dom import minidom
import array as arr
import fileinput
import os
from svglib.svglib import svg2rlg
from os import path
import webbrowser
from shutil import copyfile
import re
import time
import pprint

export = 1
debug = 0

filePath = "./templates/FullSize_1.svg"
chrome_path="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
webbrowser.register('chrome', None,webbrowser.BackgroundBrowser(chrome_path))

regexString = 'color: #000000; line-height: 1.2; pointer-events: all; white-space: normal; word-wrap: normal; "><span>BUTTON_11</span></div></div></div></foreignObject><text x="310" y="169" fill="#000000" font-family="Helvetica" font-size="12px" text-anchor="middle">REPLACED</text></switch></g><rect x="43" y="183" width="175" height="18" fill="#ffffff"'
expectedString = 'color: #000000; line-height: 1.2; pointer-events: all; white-space: normal; word-wrap: normal; "><span>REPLACED</span></div></div></div></foreignObject><text x="310" y="169" fill="#000000" font-family="Helvetica" font-size="12px" text-anchor="middle">REPLACED</text></switch></g><rect x="43" y="183" width="175" height="18" fill="#ffffff"'

buttonID = 11
regexSearch = "\\b" + "BUTTON_" + str(buttonID) + "\\b"
print(regexSearch)
regexString = re.sub(regexSearch,"REPLACED",regexString)

stringCompare = regexString == expectedString


print("String is: " + str(stringCompare))




## WORKING SOLUTIOn
# r'\"' + searchRegex + '',
# searchRegex = '>(.\BUTTON_11)'
# 
#          

# parse an xml file by name
mydoc = minidom.parse('./samples/Virpil_DCS.xml')
if debug:
    print(mydoc)

gameDevices = mydoc.getElementsByTagName('device')

if debug:
    print("Number of Devices: " + str(gameDevices.length))

# DEVICE NAME - Many in file FOREACH
for device in gameDevices:

    ## DEVICE NAME
    selectedDevice = device.getAttribute('name')
    
    if debug:
        print("-----------------------------------------------------------------")
        print(selectedDevice)

## CHECK MODES AVAILABLE
    modes = device.getElementsByTagName('mode')

# DEVICE MODES
    for mode in modes:

        buttonArr = {}
        selectedMode = mode.getAttribute('name')

        if debug:
            print("Profile: " + mode.getAttribute('name'))

# SPECIFIC TO SELECTED MODE
        buttons = mode.getElementsByTagName('button')

        #if debug:
        #    for val in buttons:
        #        if val.getAttribute('description') != "":
        #            print("")
        #            #print("Button: " + str(val.getAttribute('id')) + " - " + val.getAttribute('description'))
        #        else:   
        #            if debug:
        #                print("")
        #                #print("Button: " + str(val.getAttribute('id')) + " Not Mapped")  
        #print("-----------------------------------------------------------------")

# EDIT TEMPLATE
        pp = pprint.PrettyPrinter(indent=4)
        ## BUILD BUTTON ARRAY
        

        for i in buttons:
            if i.getAttribute('description') != "":
                buttonArr.update ({
                                    "BUTTON_" + str(i.getAttribute('id')):str(i.getAttribute('description'))
                                })
            else:
                buttonArr.update ({
                                    "BUTTON_" + str(i.getAttribute('id')): "NO BIND"
                                })

        newPath = "./temp/" + selectedDevice + "_" + selectedMode + ".svg"

        if path.exists("./templates/" + selectedDevice + ".svg"):
            copyfile("./templates/" + selectedDevice + ".svg", newPath)
           
            print("Export path is: " + newPath)
            pp.pprint(buttonArr)

            if export:

                with open(newPath,'r') as file:
                    SVG_Input = file.read()

                for b, v in buttonArr.items():
                    regexSearch = "\\b" + b + "\\b"
                    SVG_Input = re.sub(regexSearch, v, SVG_Input)
    
            
            outputPath = "./diagrams/" + selectedDevice + "_" + selectedMode + ".svg"
            outputfile = open(outputPath, "w")
            outputfile.write(SVG_Input)
            chart_path = outputPath
            webbrowser.get('chrome').open_new_tab(outputPath)

# OUTPUT FOR PRINT



#for val in buttons:
                    
               #         buttonSearch = str("BUTTON_" + val.getAttribute('id'))
              #          buttonReplace = str(val.getAttribute('description'))

               #         for line in file:
               #             print("BUTTON REPLACEMENT")

               #             if val.getAttribute('description') != "":
               #                 print("Replacing Line: Button = " + val.getAttribute('id') + " and description = " + val.getAttribute('description'))
#
               #                 print(buttonSearch)
               #                 print(buttonReplace)
          #
                #                print("Replacing Line: Button = " + val.getAttribute('id'))
                 #               line.replace(buttonSearch,buttonReplace)
                  #              print("Button: " + str(val.getAttribute('id')) + " - " + val.getAttribute('description'))
                   #         else:   
                    #            if debug:
                     #               print("Button: " + str(val.getAttribute('id')) + " Not Mapped")  
                      #              line.replace(buttonSearch,buttonReplace)


# Look at Button to Physical Mapping


# Write values out to PDF (find/replace)




# <profile version="9">
#    <devices>
#        <device device-guid="{01DE0A30-B49F-11EA-8002-444553540000}" label="" name="VPC Throttle MT-50 CM2" type="joystick">
#            <mode inherit="Base" name="A10">
#                <axis description="" id="1"/>
#                <axis description="" id="2"/>
#                <axis description="" id="3"/>
#                <axis description="" id="4"/>
#                <axis description="" id="5"/>
#                <axis description="" id="6"/>
#                <button description="" id="1"/>
#                <button description="" id="2"/>
#                <button description="" id="3"/>
#                <button description="" id="4"/>
#                <button description="Pinkie Center" id="5">
#                    <container type="basic">
#                        <action-set>
#

