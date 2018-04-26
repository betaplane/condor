from configparser import ConfigParser

config_file = '/Users/arno/Documents/GitHub/condor/general.cfg'
"name of the config file"

class config(object):
    def __init__(self):
        self.config = ConfigParser()
        self.config.read(config_file)
