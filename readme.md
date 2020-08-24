# Joystick Gremlin - Diagrams

This is an initial release - Please raise bugs/feature requests to help me improve it.

## What is this tool for?

Learning simulators is a daunting task, with lots of buttons to remember. If only there was some easy way to print out what my bindings are... onto a pretty picture of my stick!

Now there is.

- Export your joystick/throttle/custom HID buttons to a PDF
- Overlay your buttons onto an actual Joystick profile/picture

## What's supported?
- Custom SVG templates can be built to suit your joystick, throttle, custom HID device
- Support for multiple profiles in Joystick Gremlin

## What's not supported
- Importing/inheriance of base templates into button profile exports (In progress)
- Support for other programs/games
- Want a feature? Raise an issue

## Installation

### Prerequisites
Requires Python 3.7
- No install required, direct execution via Python

"py main.py"

## Usage

Please ensure you have **backup of your config**, this should not modify if but I also take no responsibility if you lose all your binds!

- Edit Config.py to point to your Joystick Gremlin config file you want to map
- Program will try match Device Names, with available files in /templates
- If it finds a match, it'll export the bindings for this device, and any modes you have configured
- If you have web browser enabled, they'll automatically open in your browser
- Files will be stored in /diagrams when export has been completed. You can open these in a web browser, and print to PDF/printer from there

## Adding Templates
There are many joysticks out there, and a template needs to be provided for them in /Templates.

This is very easy to do, for free online

1. Go to an SVG compliant editor (http://draw.io/)
2. Create a joystick profile by importing a joystick image, and creating labels
3. Call the label BUTTON_X, where X is the actual physical button on your stick
4. Export template as SVG
5. Place this in /Templates with the relevant device name seen by windows

Now on execution of the program, you should have your binds automatically added to the app.

# Limitations
- If your binding overlaps/wraps on export against your design, adjust your SVG image. The program will not automatically change your design to fit content
- Will not output to PDF, do this via your browser (open SVG from /diagrams in Chrome/Edge)
- Only supports Joystick Gremlin currently
- Highly configurable joysticks/throttles (I.e. Virpil) may need template customisation. As button 1 etc may differ from someone elses button 1
- Right now not tested with POV 8 way hats, if you're using these and have issues please get in touch and maybe share your config (if they're seen as individual buttons it'll probably work)



