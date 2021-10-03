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
CONFIG_FILE = '.mediatools.properties'
VIDEO_RESOLUTION_KEY = 'default.video.resolution'
VIDEO_FPS_KEY = 'default.video.fps'
SLIDESHOW_DURATION_KEY = 'default.slideshow.duration'

def load():
    import mediatools.utilities as util
    global CONFIG_SETTINGS, CONFIG_FILE
    target_file = "{}{}{}".format(os.path.expanduser("~"), os.sep, CONFIG_FILE)
    if not os.path.isfile(target_file):
        default_file = util.package_home() / 'media-tools.properties'
        if not os.path.isfile(default_file):
            log.logger.critical("Default configuration file %s is missing, aborting...", default_file)
            raise FileNotFoundError
        shutil.copyfile(default_file, target_file)
        log.logger.info("User configuration file %s created", target_file)
    try:
        log.logger.info("Trying to load media config %s", target_file)
        fp = open(target_file)
    except FileNotFoundError as e:
        log.logger.critical("Default configuration file %s is missing, aborting...", target_file)
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
