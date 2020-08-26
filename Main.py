import adaptors.gremlin as gremlin
import config
import functions.helper as helper

#TODO
# Release?
#
gremlin = gremlin.Gremlin(config.gremlinconfig)

devices = gremlin.createDictionary()

for joystick in devices:
    for mode in devices[joystick]:
        helper.exportDevice(devices, joystick, mode)

print("----------------FINISHED-------------------")
print("View your outputted files in /diagrams and open them in a web browser to print.")
print("-------------------------------------------")
