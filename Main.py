import adaptors.joystick_gremlin as adaptor
import config
import functions.helper as helper

#TODO
# Add tests
# Build EXE?
# Add more templates? Warthog? Virpil Sticks
# Release?
#

gremlinconfig = adaptor.Gremlin('./samples/Virpil_DCS.xml')
devices = gremlinconfig.getDevices()

for joystick in devices:
    for mode in devices[joystick]:
        helper.exportDevice(devices, joystick, mode)