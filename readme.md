# Joystick Diagrams (Engine)

<div align="center">

  ![Joystick Diagrams Logo](https://joystick-diagrams.com/img/logo.png)

  [![Release](https://img.shields.io/github/v/release/Rexeh/joystick-diagrams?include_prereleases&style=flat-square)](https://github.com/Rexeh/joystick-diagrams/releases)
  [![License](https://img.shields.io/github/license/Rexeh/joystick-diagrams?style=flat-square)](https://github.com/Rexeh/joystick-diagrams/blob/main/LICENSE)
  [![GitHub Stars](https://img.shields.io/github/stars/Rexeh/joystick-diagrams?style=flat-square)](https://github.com/Rexeh/joystick-diagrams/stargazers)
  [![GitHub Issues](https://img.shields.io/github/issues/Rexeh/joystick-diagrams?style=flat-square)](https://github.com/Rexeh/joystick-diagrams/issues)
  [![Downloads](https://img.shields.io/github/downloads/Rexeh/joystick-diagrams/total?style=flat-square)](https://github.com/Rexeh/joystick-diagrams/releases)
  ![Discord](https://img.shields.io/discord/733253732355276800?label=Discord)

  **Your bindings, visualized in seconds.**

  Automatically create hardware-accurate visual reference cards for your HOTAS setup, directly from your game configuration files. A number of plugins for popular games and tools, if one is missing create your own with ease!

  [Download Free](https://github.com/Rexeh/joystick-diagrams/releases) · [Documentation](https://joystick-diagrams.com/setup/) · [Report Bug](https://github.com/Rexeh/joystick-diagrams/issues) · [Request Feature](https://discord.com/channels/733253732355276800/1212843539223027753)

</div>

---

## What is Joystick Diagrams?

Joystick Diagrams reads your game config files and generates hardware-accurate visual diagrams of every button, axis, hat switch, and modifier on your controllers.

No manual data entry. No design skills needed. Always in sync with your actual bindings.

**If you've ever found yourself:**
- Memorizing bindings through repetition
- Building reference cards in PowerPoint or Photoshop by hand
- Printing ugly, unreadable binding lists from the game settings
- Pausing mid-flight to check which button does what

...this is what I built it to fix.

## Supported Games/Tools
The engine has no support built in, instead relying on plugins (official and 3rd party) to provide capabilities for games and tools. These can be directly installed from the engine itself.

**A full list is available on the website:***
 https://joystick-diagrams.com/plugins/

More games can be added through the open plugin system.

### Building from Source

```bash
git clone https://github.com/Rexeh/joystick-diagrams.git
cd joystick-diagrams
uv sync
```

## Community

- **Discord.** Join the [Joystick Diagrams Discord](https://discord.gg/JC5QFMB) for support, template sharing, and feature requests.
- **Issues.** Report bugs via [GitHub Issues](https://github.com/Rexeh/joystick-diagrams/issues).
- **Templates.** Community members contribute new device templates regularly.

## Contributing
- Template creation (More template support the better, if you own a device not yet covered, create a template for others to enjoy!)
  - Details on website - https://joystick-diagrams.com/templates/custom/
- Plugin creation - A full API is available to create your own plugins for users to install
  - https://joystick-diagrams.com/developers/


## License

Distributed under the GPL-2.0 License. See [LICENSE](LICENSE) for more information.
