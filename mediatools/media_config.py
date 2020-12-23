import os
import shutil
import jprops

CONFIG_SETTINGS = {}
CONFIG_FILE = '.mediatools.properties'

def load():
    import pathlib
    import mediatools.utilities as util
    global CONFIG_SETTINGS, CONFIG_FILE
    target_file = "{}{}{}".format(os.path.expanduser("~"), os.sep, CONFIG_FILE)
    if not os.path.isfile(target_file):
        default_file = pathlib.Path(__file__).parent / 'media-tools.properties'
        if not os.path.isfile(default_file):
            util.logger.critical("Default configuration file %s is missing, aborting...", default_file)
            raise FileNotFoundError
        shutil.copyfile(default_file, target_file)
        util.logger.info("User configuration file %s created", target_file)
    try:
        util.logger.info("Trying to load media config %s", target_file)
        fp = open(target_file)
    except FileNotFoundError:
        util.logger.critical("Default configuration file %s is missing, aborting...", target_file)
        raise FileNotFoundError
    CONFIG_SETTINGS = jprops.load_properties(fp)
    fp.close()
    for key, value in CONFIG_SETTINGS.items():
        value = value.lower()
        if value == 'yes' or value == 'true' or value == 'on':
            CONFIG_SETTINGS[key] = True
            continue
        if value == 'no' or value == 'false' or value == 'off':
            CONFIG_SETTINGS[key] = False
            continue
        try:
            intval = int(value)
            CONFIG_SETTINGS[key] = intval
        except ValueError:
            pass

    return CONFIG_SETTINGS


def get_property(name, settings=None):
    if settings is None:
        global CONFIG_SETTINGS
        settings = CONFIG_SETTINGS
    return settings.get(name, '')