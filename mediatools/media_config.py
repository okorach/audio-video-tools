#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import os
import shutil
import jprops
from mediatools import log

CONFIG_SETTINGS = {}
BASE_CONFIG_FILE = '.mediatools.properties'
FULL_CONFIG_FILE = None
VIDEO_RESOLUTION_KEY = 'default.video.resolution'
VIDEO_FPS_KEY = 'default.video.fps'
SLIDESHOW_DURATION_KEY = 'default.slideshow.duration'

def load():
    import mediatools.utilities as util
    global CONFIG_SETTINGS, BASE_CONFIG_FILE, FULL_CONFIG_FILE
    if CONFIG_SETTINGS:
        return CONFIG_SETTINGS
    FULL_CONFIG_FILE = f'{os.path.expanduser("~")}{os.sep}{BASE_CONFIG_FILE}'
    if not os.path.isfile(FULL_CONFIG_FILE):
        default_file = util.package_home() / 'media-tools.properties'
        if not os.path.isfile(default_file):
            log.logger.critical("Default configuration file %s is missing, aborting...", default_file)
            raise FileNotFoundError
        shutil.copyfile(default_file, FULL_CONFIG_FILE)
        log.logger.info("User configuration file %s created", FULL_CONFIG_FILE)
    try:
        log.logger.info("Trying to load media config %s", FULL_CONFIG_FILE)
        fp = open(FULL_CONFIG_FILE)
    except FileNotFoundError as e:
        log.logger.critical("Default configuration file %s is missing, aborting...", FULL_CONFIG_FILE)
        raise FileNotFoundError from e
    CONFIG_SETTINGS = jprops.load_properties(fp)
    fp.close()
    for key, value in CONFIG_SETTINGS.items():
        value = value.lower()
        if value in ('yes', 'true', 'on'):
            CONFIG_SETTINGS[key] = True
            continue
        if value in ('no', 'false', 'off'):
            CONFIG_SETTINGS[key] = False
            continue
        try:
            newval = int(value)
            CONFIG_SETTINGS[key] = newval
        except ValueError:
            pass
        try:
            newval = float(value)
            CONFIG_SETTINGS[key] = newval
        except ValueError:
            pass

    return CONFIG_SETTINGS


def get_property(name, settings=None):
    if settings is None:
        global CONFIG_SETTINGS
        settings = CONFIG_SETTINGS
    return settings.get(name, None)


def get_config_file():
    global FULL_CONFIG_FILE
    return FULL_CONFIG_FILE


def reload():
    global CONFIG_SETTINGS
    CONFIG_SETTINGS = {}
    load()
