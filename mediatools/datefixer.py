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

import sys
import argparse
import re
from exiftool import ExifToolHelper
import mediatools.utilities as util
import mediatools.log as log
import utilities.file as fil
from mediatools import videofile
from datetime import datetime
from dateutil.relativedelta import relativedelta



def guess_date(string: str) -> datetime | None:
    """Sets a file date from date or datetime that should be in the filename"""
    (year, mon, day, hour, min, sec) = (0, 0, 0, 0, 0, 0)
    log.logger.info("Searching a date in %s", string)
    # 2017-05-07 08.13.42
    sep = r"[-:_\. hm]"
    m = re.search(rf"(\d\d\d\d){sep}(\d\d){sep}(\d\d){sep}(\d\d){sep}(\d\d){sep}(\d\d)", string)
    if not m:
        # 20170507_123422
        m = re.search(rf"(\d\d\d\d)(\d\d)(\d\d){sep}(\d\d)(\d\d)(\d\d)", string)
    if m:
        (year, mon, day, hour, min, sec) = [int(m.group(i+1)) for i in range(6)]
    else:
        # 2017-05-07
        m = re.search(rf"(\d\d\d\d){sep}(\d\d){sep}(\d\d)", string)
        if m:
            (year, mon, day) = [int(m.group(i+1)) for i in range(3)]
            (hour, min, sec) = (0, 0, 0)
    if not m:
        log.logger.warning("No date match for %s", string)
        return None
    return datetime(year, mon, day, hour, min, sec)

def guess_offset(string: str) -> relativedelta | None:
    sign = int(f"{string[0]}1")
    rest = string[1:]
    (year, month, day, hour, min, sec) = (0, 0, 0, 0, 0, 0)
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$", rest)
    if m:
        print(f"{str(m.group())}")
        [year, month, day, hour, min, sec] = [int(m.group(i+1)) * sign for i in range(6)]
    else:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", rest)
        if m:
            [year, month, day] = [int(m.group(i+1)) * sign for i in range(3)]
        else:
            m = re.match(r"^(\d{2}):(\d{2}):(\d{2})$", rest)
            if m:
                [hour, min, sec] = [int(m.group(i+1)) * sign for i in range(3)]
    if not m:
        print("Not [+-]YYYY-MM-DD hh:mm:ss nor YYYY-MM-DD nor hh:mm:ss")
        return None
    return relativedelta(years=year, months=month, days=day, hours=hour, minutes=min, seconds=sec)


def change_files_date(change_mode: str, * file_list) -> int:
    nb_success = 0
    nb_files = len(file_list)
    seq = 1
    for file in file_list:
        log.logger.info("Processing file %d/%d for %s", seq, nb_files, file)
        if change_mode == "auto":
            videofile.get_exif(file)
            new_date = guess_date(fil.basename(file))
            if new_date and videofile.set_creation_date(file, new_date):
                nb_success += 1
        elif change_mode[0] in ('-', '+'):
            offset = guess_offset(change_mode)
            if offset and videofile.set_creation_date(file, videofile.get_creation_date(file) + offset):
                nb_success += 1
        else:
            new_date = guess_date(change_mode)
            if new_date and videofile.set_creation_date(file, new_date):
                nb_success += 1
        seq += 1
    log.logger.info("Processed all files. Success rate %d/%d or %d%%", nb_success, nb_files, int(nb_success*100/nb_files))
    return nb_success

def main() -> None:
    util.init('renamer')
    parser = argparse.ArgumentParser(description='Stacks images vertically or horizontally')
    parser.add_argument('-f', '--files', nargs='+', help='List of files to rename', required=True)
    parser.add_argument('--offset', help='Time to add or remove, prefix with - to remove', required=False)
    parser.add_argument('--year', help='Proper year of the file', required=False)
    parser.add_argument('-g', '--debug', required=False, type=int, help='Debug level')
    kwargs = util.parse_media_args(parser)

    file_list = fil.file_list(*kwargs['files'], file_type=None, recurse=False)
    file_list = [f for f in file_list if fil.extension(f).lower() in ('jpg', 'mp4', 'jpeg', 'gif', 'png', 'mp2', 'mpeg', 'mpeg4', 'mpeg2', 'vob', 'mov')]
    if "offset" in kwargs:
        change_files_date(kwargs['offset'], * file_list)
    elif "year" in kwargs:
        good_year = int(kwargs["year"])
        bad_file, good_file = None, None
        if len(file_list) != 2:
            log.logger.error("You must pass exactly 2 files to move creation date between files")
            sys.exit(1)
        for filename in file_list:
            log.logger.info("Processing file %s", filename)
            if videofile.get_creation_date(filename).year == good_year:
                good_file = filename
            else:
                bad_file = filename
        if good_file is not None and bad_file is not None:
            videofile.set_creation_date(bad_file, videofile.get_creation_date(good_file))
        else:
            log.logger.error("Can't detect file with bad date and good date")
            sys.exit(1)

    else:
        log.logger.error("--offset or --year must be specified")
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
