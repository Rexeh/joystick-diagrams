# Joystick Diagrams - Plugins

> [!CAUTION]
> All information here is subject to change during the course of 2.0 pre-release. If you want to build a plugin based off this, then please get in touch on Discord to work together.

## Parser Plugins
With version 2.0, Joystick Diagrams has moved to a plugin system to allow further games to be supported faster.

## Plugin Structure
-  plugins/ - Directory for plugins
   - *plugin name*
     - \__init\__.py
     - main.py - Main interface for Joystick Diagrams
     - config.py - Base configuration using Dynaconf for Plugin requirements

## main.py
main.py **must** follow the signature of plugin_interface

### set_path()
Joystick Diagrams will orchestrate collection of a directory or file from user input, which will be injected as a [Pathlib Path](https://docs.python.org/3/library/pathlib.html) object.

As part of this, you should perform any relevant validation on the supplied Path, such as checking that it can be parsed.

Plugins are responsible for **storing** this validated path for the tool to restore state on new application runs.

### process()
Joystick Diagrams will orchestrate your process method automatically from the UI. This will return a ProfileCollection() from your processing code.

### path_type()
As part of your Plugin creation, you must define a valid **FilePath** or **FolderPath** as part of the path_type property. This will be used to display information on the front end such as dialog help, default directories and file types.

### Example Plugin
One is included in the library - https://github.com/Rexeh/joystick-diagrams/tree/master/joystick_diagrams/plugins/Example/examplePlugin


## 3rd Party Module usage
At this time, Plugins can only use native Python packages or those utilised by 1st party modules. If you should require some additional libraries in order to write your plugin then open for discussion.

## Configuration Management
Parser Plugins are responsible for their own configuration, choice of how to persist the data for your plugin is yours, but you can also follow convention.

### load_data()
This method should restore any relevant data to your plugin. load_data() is called as part of the plugin loading mechanism.

A key part of load data should be setting your path attribute to any stored value, which will trigger set_path() method to be called to automatically revalidate the path against your plugin.

### Dynaconf
Core Plugin Configuration is provided by Dynaconf **config.py** and the chosen format is JSON for configuration store.

Dynaconf can be used as a write store also, but this is down to individual plugins to decide, generally 

You can retrieve settings for your plugin using **settings.VARIABLE**, for further usage and validation see [Dynaconf Documentation](https://www.dynaconf.com/)