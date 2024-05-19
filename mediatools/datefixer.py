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

import argparse
from exiftool import ExifToolHelper
import mediatools.utilities as util
import mediatools.log as log
import mediatools.file as fil
from datetime import datetime
from dateutil.relativedelta import relativedelta

def __get_creation_date(filename):
    with ExifToolHelper() as et:
        for exif_data in et.get_metadata(filename):
            creation_date = util.get_creation_date(exif_data)
    return creation_date


def set_file_date(filename, new_date) -> None:
    log.logger.info("Setting creation date of %s to %s", filename, new_date)
    p = ["-P", "-overwrite_original"]
    with ExifToolHelper() as et:
        if fil.is_image_file(filename):
            et.set_tags([filename], tags={"DateTimeOriginal": new_date}, params=p)
        elif fil.is_video_file(filename):
            log.logger.info("Tagging video file")
            et.set_tags([filename], tags={
                "CreateDate": new_date,
                "ModifyDate": new_date,
                "DateTimeOriginal": new_date
            }, params=p)
            et.set_tags([filename], tags={
                # "CreateDate": new_date,
                # "ModifyDate": new_date,
                # "DateTimeOriginal": new_date,
                "EXIF:CreateDate": new_date,
                "EXIF:ModifyDate": new_date,
                "EXIF:DateTimeOriginal": new_date
            }, params=p)
            et.set_tags([filename], tags={
                "Composite:SubSecCreateDate": new_date,
                "Composite:SubSecDateTimeOriginal": new_date,
                "Composite:SubSecModifyDate": new_date,
                "Quicktime:CreateDate": new_date,
                "Quicktime:DateTimeOriginal": new_date,
                "QuickTime:MediaCreateDate": new_date,
                "QuickTime:MediaModifyDate": new_date,
                "QuickTime:TrackCreateDate": new_date,
                "QuickTime:TrackModifyDate": new_date,
                "QuickTime:CreateDate": new_date,
                "QuickTime:ModifyDate": new_date
            }, params=p)


def main() -> None:
    util.init('renamer')
    parser = argparse.ArgumentParser(description='Stacks images vertically or horizontally')
    parser.add_argument('-f', '--files', nargs='+', help='List of files to rename', required=True)
    parser.add_argument('--offset', help='Time to add or remove, prefix with - to remove', required=True)
    parser.add_argument('-g', '--debug', required=False, type=int, help='Debug level')
    kwargs = util.parse_media_args(parser)

    file_list = fil.file_list(*kwargs['files'], file_type=None, recurse=False)
    seq = 1
    nb_files = len(file_list)
    sign = 1
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
            set_file_date(filename, absolute_date)
        else:
            set_file_date(filename, datetime.strftime(__get_creation_date(filename) + offset, util.EXIF_DATE_FMT))
        seq += 1


if __name__ == "__main__":
    main()
