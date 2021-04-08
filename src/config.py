import configparser as ConfigParser
from pathlib import Path

Config = ConfigParser.ConfigParser()
Config.read("./config.cfg")

# Write logs
debug = Config.getboolean("Logging", "EnableLogging", fallback=1)
debugLevel = Config.getint("Logging", "LogLevel", fallback=1)

# Params
noBindText = Config.get("Preferences", "NoBindText", fallback="No Bind")

# Export out SVG files - for development only (leave as = 1)
export = 1

## Program can automatically open in browser as it creates, specify below if you want this. Only supports Chrome right now.
openinbrowser = Config.getboolean("BROWSER", "OpenTemplatesInBrowser", fallback=0)
chrome_path = Config.get("BROWSER", "ChromePath", fallback="")
