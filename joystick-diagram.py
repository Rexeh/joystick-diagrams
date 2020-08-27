import adaptors.gremlin as gremlin
import config
import functions.helper as helper

print(helper.getVersion())

if config.gremlinconfig == "":
    print("Please edit config.cfg to specify your Joystick Gremlin config .XML file location")
    input("Press enter to exit")
else:
    gremlin = gremlin.Gremlin(config.gremlinconfig)

    devices = gremlin.createDictionary()

    for joystick in devices:
        for mode in devices[joystick]:
            helper.exportDevice(devices, joystick, mode)

print("----------------FINISHED-------------------")
print("View your outputted files in /diagrams and open them in a web browser to print.")
print("-------------------------------------------")

input("Press enter to exit")