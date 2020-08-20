from xml.dom import minidom
import array as arr
import fileinput
import os
from svglib.svglib import svg2rlg
import webbrowser
from shutil import copyfile

export = 1
debug = 1

filePath = "./templates/FullSize_1.svg"
chrome_path="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
webbrowser.register('chrome', None,webbrowser.BackgroundBrowser(chrome_path))

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

        selectedMode = mode.getAttribute('name')

        if debug:
            print("Profile: " + mode.getAttribute('name'))

# SPECIFIC TO SELECTED MODE
        buttons = mode.getElementsByTagName('button')

        if debug:
            for val in buttons:
                if val.getAttribute('description') != "":
                    print("Button: " + str(val.getAttribute('id')) + " - " + val.getAttribute('description'))
                else:   
                    if debug:
                        print("Button: " + str(val.getAttribute('id')) + " Not Mapped")  
        print("-----------------------------------------------------------------")

# EDIT TEMPLATE

        newPath = "./temp/" + selectedDevice + "_" + selectedMode + ".svg"
        copyfile("./templates/FullSize_1.svg", newPath)

        print(newPath)

        if export:
            with fileinput.FileInput(newPath, inplace=True) as file:
                for line in file:
                    print(line.replace("BUTTONVALUE", str(selectedDevice)), end='')

            chart_path = newPath
            webbrowser.get('chrome').open_new_tab(newPath)

# OUTPUT FOR PRINT




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

