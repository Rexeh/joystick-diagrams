# Templates

Define templates in SVG. Name of template should match your Joystick Gremlin device name.

# Default Templates

## Virpil
- Virpil MT50-CM2 Stick
- Virpil MT50-CM2 Throttle
- Virpil Constellation Alpha-R
- Virpil Constellation Alpha-L
- Virpil Constellation Delta
- Virpil WarBRD Grip
- Virpil MT50 Throttle V2

## Thrustmaster
- Warthog HOTAS
- Warthog Throttle

## Missing your stick?

### Adding Templates
There are many joysticks out there, and a template needs to be provided for them in /Templates.

This is very easy to do, for free online

1. Go to an SVG compliant editor (http://draw.io/) and open CustomTemplate.SVG
2. Create a joystick profile by importing a joystick image, and creating labels
3. Call the label BUTTON_X, where X is the actual physical button on your stick
4. Export template as SVG
5. Place this in /Templates with the relevant device name seen by windows

Now on execution of the program, you should have your binds automatically added to the app.

If you have created a template, happy to include it back in the repository (might make some edits to standardise it)
