from xml.dom import minidom
import config
import functions.helper as helper

class Gremlin:
## Adaptor for JG

    def __init__(self,filepath):
    ## TRY FIND PATH
        self.file = minidom.parse(filepath)
        
    ## RETURN ERROR

    def getDevices(self):
        
        devices = self.file.getElementsByTagName('device')

        helper.log("Number of Devices: ",str(devices.length))

        arr = {}

        for device in devices:
            
            ## DEVICE NAME
            selectedDevice = device.getAttribute('name')
            modes = device.getElementsByTagName('mode')
            
            helper.log("All Modes: ",modes)

            for mode in modes:
                buttonArr = {}
                selectedMode = mode.getAttribute('name')
                
                helper.log("Selected Mode: ",selectedMode)
                helper.log("Profile: ",mode.getAttribute('name'))

                buttons = mode.getElementsByTagName('button')
            
                for i in buttons:
                    if i.getAttribute('description') != "":
                        buttonArr.update ({
                                            "BUTTON_" + str(i.getAttribute('id')):str(i.getAttribute('description'))
                                        })
                    else:
                        buttonArr.update ({
                                        "BUTTON_" + str(i.getAttribute('id')): "NO BIND"
                                        })
                
                helper.updateDeviceArray(arr,selectedDevice,selectedMode,buttonArr)
                
        return arr
  
   

#gameDevices = gremlin.getElementsByTagName('device')



# DEVICE NAME - Many in file FOREACH
#for device in gameDevices:
    
    ## DEVICE NAME
#    selectedDevice = device.getAttribute('name')
#    modes = device.getElementsByTagName('mode')

#    for mode in modes:

#        buttonArr = {}
#        selectedMode = mode.getAttribute('name')

#        if config.debug:
#            print("Profile: " + mode.getAttribute('name'))

#        buttons = mode.getElementsByTagName('button')

#        if config.debug:
#            for val in buttons:
#                if val.getAttribute('description') != "":
#                    print("Button: " + str(val.getAttribute('id')) + " - " + val.getAttribute('description'))
#                else:   
#                    if config.debug:
#                        print("Button: " + str(val.getAttribute('id')) + " Not Mapped")  
#        print("-----------------------------------------------------------------")
        
#        for i in buttons:
#            if i.getAttribute('description') != "":
#                buttonArr.update ({
#                                    "BUTTON_" + str(i.getAttribute('id')):str(i.getAttribute('description'))
#                                })
#            else:
#                buttonArr.update ({
#                                   "BUTTON_" + str(i.getAttribute('id')): "NO BIND"
#                                })