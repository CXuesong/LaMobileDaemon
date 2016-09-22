from configparser import ConfigParser

config = ConfigParser()
config.read("Confidential/LaMobile.ini")

def GetConfig(section, key, defaultValue=None) :
    return config.get(section, key, fallback=defaultValue)

def SetConfig(section, key, value) :
    if not config.has_section(section) : config.add_section(section)
    config.set(section, key, str(value))

def SaveConfig() :
    with open('Confidential/LaMobile.ini', 'w') as configfile:
        config.write(configfile)
