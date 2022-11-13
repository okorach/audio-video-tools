#!python3
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
import logging
import pathlib

logger = logging.getLogger('mediatools')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
try:
    fh = logging.FileHandler('mediatools.log')
except PermissionError:
    fallback_log = pathlib.Path(os.getenv("TMP", "/")) / 'mediatools.log'
    fh = logging.FileHandler(fallback_log)

# fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)
logger.addHandler(fh)
logger.addHandler(ch)
fh.setFormatter(formatter)
ch.setFormatter(formatter)


def set_logger(name):
    global logger
    logger = logging.getLogger(name)
    try:
        new_fh = logging.FileHandler(name + '.log')
    except PermissionError:
        fallback_log = pathlib.Path(os.getenv("TMP", "/")) / (name + '.log')
        new_fh = logging.FileHandler(fallback_log)
    new_ch = logging.StreamHandler()
    logger.addHandler(new_fh)
    logger.addHandler(new_ch)
    new_fh.setFormatter(formatter)
    new_ch.setFormatter(formatter)


def get_logging_level(intlevel):
    if intlevel >= 4:
        lvl = logging.DEBUG
    elif intlevel >= 3:
        lvl = logging.INFO
    elif intlevel >= 2:
        lvl = logging.WARNING
    elif intlevel >= 1:
        lvl = logging.ERROR
    else:
        lvl = logging.CRITICAL
    return lvl
