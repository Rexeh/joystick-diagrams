from xml.dom import minidom
import array as arr
import PyPDF2
from PyPDF2 import PdfFileWriter, PdfFileReader
import docx
from zipfile import ZipFile 
import fileinput
import shutil
import os
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF, renderPM
import webbrowser

export = 0
debug = 1

# parse an xml file by name
mydoc = minidom.parse('./samples/Virpil_DCS.xml')
if debug:
    print(mydoc)

gameDevices = mydoc.getElementsByTagName('device')

if debug:
    print("Number of Devices: " + str(gameDevices.length))

## Search for Particular Device / NOT IMPLEMENTED TO FILTER
deviceName = "VPC Throttle MT-50 CM2"

profileName = "A10" #IF USING PROFILES, BASE NEEDS TO BE MERGED

# DEVICE NAME - Many in file FOREACH

for device in gameDevices:
    print(device.getAttribute('name'))

## CHECK EXISTS > TEMPLATE
    modes = device.getElementsByTagName('mode')
# DEVICE MODE - MANY IN FILE

    if debug:
        print("Modes Found")

# DEVICE MODE NAME OPTIONAL
    for mode in modes:
        mode.getAttribute('name')

        if debug:
            print("Profile: " + mode.getAttribute('name'))

            print("-----------------------------------------------------------------")

# SPECIFIC TO SELECTED MODE
        buttons = mode.getElementsByTagName('button')

        if debug:
            for val in buttons:
                if val.getAttribute('description') != "":
                    print("Button: " + str(val.getAttribute('id')) + " - " + val.getAttribute('description'))
                else:   
                    if debug:
                        print("Button: " + str(val.getAttribute('id')) + " Not Mapped")  

# EDIT TEMPLATE

if export:
    with fileinput.FileInput("./FullSize_1.svg", inplace=True, backup='.bak') as file:
        for line in file:
            print(line.replace("ThisIsATest", "BUTTON MAPPING - GREMLIN"), end='')

    print(webbrowser._browsers)

    chart_path = "FullSize_1.svg"

    urL='https://www.google.com'
    chrome_path="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
    webbrowser.register('chrome', None,webbrowser.BackgroundBrowser(chrome_path))
    webbrowser.get('chrome').open_new_tab(chart_path)

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

