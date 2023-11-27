import configparser as ConfigParser

Config = ConfigParser.ConfigParser()
Config.read("./config.cfg")

# Logging
debugLevel = Config.get("Logging", "LogLevel", fallback="INFO")

# Params
noBindText = Config.get("Preferences", "NoBindText", fallback="No Bind")
