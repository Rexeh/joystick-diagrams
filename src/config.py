import configparser as ConfigParser
from pathlib import Path

Config = ConfigParser.ConfigParser()
Config.read('./config.cfg')

# Write logs
debug = Config.getboolean('DEFAULT', 'EnableLogging')
debugLevel = Config.getint('DEFAULT', 'LogLevel')

# Export out SVG files - for development only (leave as = 1)
export = 1

## Program can automatically open in browser as it creates, specify below if you want this. Only supports Chrome right now.
openinbrowser = Config.getboolean('BROWSER', 'OpenTemplatesInBrowser')
chrome_path=Config.get('BROWSER', 'ChromePath')
