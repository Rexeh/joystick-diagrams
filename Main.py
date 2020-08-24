import adaptors.gremlin as gremlin
import config
import functions.helper as helper

#TODO
# Add tests
# Build EXE?
# Add more templates? Warthog? Virpil Sticks
# Release?
#
gremlin = gremlin.Gremlin(config.gremlinconfig)

devices = gremlin.parse()

for joystick in devices:
    for mode in devices[joystick]:
        helper.exportDevice(devices, joystick, mode)