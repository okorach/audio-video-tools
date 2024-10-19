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
from exiftool import ExifToolHelper
import mediatools.utilities as util
import mediatools.log as log
import utilities.file as fil
from mediatools import videofile
from datetime import datetime
from dateutil.relativedelta import relativedelta



def main() -> None:
    util.init('renamer')
    parser = argparse.ArgumentParser(description='Stacks images vertically or horizontally')
    parser.add_argument('-f', '--files', nargs='+', help='List of files to rename', required=True)
    parser.add_argument('--offset', help='Time to add or remove, prefix with - to remove', required=False)
    parser.add_argument('--year', help='Proper year of the file', required=False)
    parser.add_argument('-g', '--debug', required=False, type=int, help='Debug level')
    kwargs = util.parse_media_args(parser)

    file_list = fil.file_list(*kwargs['files'], file_type=None, recurse=False)
    seq = 1
    nb_files = len(file_list)
    sign = 1
    if "offset" in kwargs:
        str_offset = kwargs['offset']
        type_fix = "RELATIVE"
        if str_offset[0] == '-':
            sign = -1
            str_offset = str_offset[1:]
        elif str_offset[0] == '+':
            str_offset = str_offset[1:]
        else:
            type_fix = "ABSOLUTE"
            absolute_date = datetime.strftime(datetime.strptime(str_offset, util.ISO_DATE_FMT), util.EXIF_DATE_FMT)
        [year, month, day] = [0, 0, 0]
        if " " in str_offset:
            [dt, str_offset] = str_offset.split(" ")
            [year, month, day] = [int(i) * sign for i in dt.split("-")]

        [h, m, s] = [int(i) * sign for i in str_offset.split(":")]
        offset = relativedelta(years=year, months=month, days=day, hours=h, minutes=m, seconds=s)

        if type_fix == "ABSOLUTE":
            log.logger.info("%d files to process, absolute date = %s", nb_files, str(absolute_date))
        else:
            log.logger.info("%d files to process, relative offset = %s", nb_files, str(offset))
        for filename in file_list:
            log.logger.info("Processing file %d/%d for %s", seq, nb_files, filename)
            if fil.extension(filename).lower() not in ('jpg', 'mp4', 'jpeg', 'gif', 'png', 'mp2', 'mpeg', 'mpeg4', 'mpeg2', 'vob', 'mov'):
                continue

            if type_fix == "ABSOLUTE":
                videofile.set_creation_date(filename, absolute_date)
            else:
                videofile.set_creation_date(filename, datetime.strftime(videofile.get_creation_date(filename) + offset, util.EXIF_DATE_FMT))
            seq += 1
    elif "year" in kwargs:
        good_year = int(kwargs["year"])
        bad_file, good_file = None, None
        if len(file_list) != 2:
            log.logger.error("You must pass exactly 2 files to move creation date between files")
            sys.exit(1)
        for filename in file_list:
            log.logger.info("Processing file %d/%d for %s", seq, nb_files, filename)
            if fil.extension(filename).lower() not in ('jpg', 'mp4', 'jpeg', 'gif', 'png', 'mp2', 'mpeg', 'mpeg4', 'mpeg2', 'vob', 'mov'):
                continue
            if __get_creation_date(filename).year == good_year:
                good_file = filename
            else:
                bad_file = filename
        if good_file is not None and bad_file is not None:
            set_file_date(bad_file, datetime.strftime(__get_creation_date(good_file), util.EXIF_DATE_FMT))
        else:
            log.logger.error("Can't detect file with bad date and good date")
            sys.exit(1)

    else:
        log.logger.error("--offet or --move must be specified")
        sys.exit(1)




    sys.exit(0)

if __name__ == "__main__":
    main()
