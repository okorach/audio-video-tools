import jprops


def load(config_file=None):
    import pathlib
    import mediatools.utilities as util
    global CONFIG_SETTINGS
    file_to_load = config_file
    # FIXME - Not working - That what I need to do
    if file_to_load is None:
        file_to_load = pathlib.Path(__file__).parent / 'media-tools.properties'

    try:
        util.logger.info("Trying to load media config %s", file_to_load)
        fp = open(file_to_load)
    except FileNotFoundError:
        if config_file is None:
            file_to_load = pathlib.Path(__file__).parent / 'media-tools.properties'
        else:
            file_to_load = pathlib.Path(__file__).parent / config_file
        util.logger.info("Loading default media config %s", config_file)
        fp = open(file_to_load)
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