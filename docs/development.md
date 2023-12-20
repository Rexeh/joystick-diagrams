# Development
The tool is currently undergoing a V2 release, so major changes will be taking place, for any development questions or to help out with development get in touch.

## Prerequisites
- Poetry
- Python 3.11 x64

## Repository Setup

1. Install Poetry for your system (https://python-poetry.org/docs/)
2. Setup a venv for Joystick Diagrams **python -m venv venv**
3. Run **poetry install**

You should now have the relevant things installed to develop Joystick Diagrams, if you run into any issues join our Discord server for support.

## Building executables
The easiest way to do this is via Make (https://gnuwin32.sourceforge.net/packages/make.htm), and using the included MakeFile.

**make build-exe**

This will build the standalone binary package, as well as the installer package for output in **/build**

[!NOTE]
Note that the build will need to take place on the target OS for deployment which for Joystick Diagrams is Windows. While the tool does support cross-platform, no need has yet come up to compile for Linux/Mac

## Developer Documentation

- Plugins [(LINK)](./docs/development/plugins.md)