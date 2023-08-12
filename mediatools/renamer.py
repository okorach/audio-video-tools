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

'''
This script renames files with format YYYY-MM-DD_HHMMSS_<root>
'''

import os
import argparse
from exiftool import ExifToolHelper
import mediatools.utilities as util
import mediatools.log as log
import mediatools.file as fil
from datetime import datetime

def main():
    util.init('renamer')
    parser = argparse.ArgumentParser(description='Stacks images vertically or horizontally')
    parser.add_argument('-f', '--files', nargs='+', help='List of files to rename', required=True)
    parser.add_argument('-r', '--root', help='Root name', required=True)
    parser.add_argument('-g', '--debug', required=False, type=int, help='Debug level')
    kwargs = util.parse_media_args(parser)
    root = kwargs['root']
    for file in kwargs['files']:
        with ExifToolHelper() as et:
            for data in et.get_tags(file, tags=["DateTimeOriginal"]):
                # 2023:07:26 08:36:01
                log.logger.debug("Data = %s", util.json_fmt(data))
                creation_date = datetime.strptime(data["EXIF:DateTimeOriginal"], '%Y:%m:%d %H:%M:%S')
        new_filename = creation_date.strftime("%Y-%m-%d %H_%M_%S") + f" {root}." + fil.extension(file)
        dirname = fil.dirname(file)
        log.logger.info(f"Renaming {file} into {dirname}{os.sep}{new_filename}")
        try:
            os.rename(file, f"{dirname}{os.sep}{new_filename}")
        except os.error:
            util.logger.warning("Unable to rename")


if __name__ == "__main__":
    main()
