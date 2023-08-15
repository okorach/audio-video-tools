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

ISO_DATE_FMT = "%Y-%m-%d %H:%M:%S"
EXIF_DATE_FMT = "%Y:%m:%d %H:%M:%S"
TIME_FMT = "%H:%M:%S"

def get_creation_date(exif_data):
    if "EXIF:DateTimeOriginal" in exif_data:
        str_date = exif_data["EXIF:DateTimeOriginal"]
    elif "File:FileModifyDate" in exif_data:
        str_date = exif_data["File:FileModifyDate"]
    else:
        log.logger.warning("Can't find creation date in %s", util.json_fmt(exif_data))
        return None

    try:
        creation_date = datetime.strptime(str_date, EXIF_DATE_FMT)
    except ValueError:
        creation_date = datetime.strptime(str_date, ISO_DATE_FMT)
    return creation_date


def main():
    util.init('renamer')
    parser = argparse.ArgumentParser(description='Stacks images vertically or horizontally')
    parser.add_argument('-f', '--files', nargs='+', help='List of files to rename', required=True)
    parser.add_argument('--add_time', help='Time to add', required=False)
    parser.add_argument('--remove_time', help='Time to remove', required=False)
    parser.add_argument('-g', '--debug', required=False, type=int, help='Debug level')
    kwargs = util.parse_media_args(parser)

    file_list = fil.file_list(*kwargs['files'], file_type=None, recurse=False)
    seq = 1
    nb_files = len(file_list)
    epoc = datetime(1900, 1, 1)
    if "remove_time" in kwargs and kwargs["remove_time"] not in (None, ""):
        if len(kwargs['remove_time']) > 8:
            offset = epoc - datetime.strptime(kwargs['remove_time'], ISO_DATE_FMT)
        else:
            offset = epoc - datetime.strptime(kwargs['remove_time'], TIME_FMT)
    if "add_time" in kwargs and kwargs["add_time"] not in (None, ""):
        if len(kwargs['add_time']) > 8:
            offset = datetime.strptime(kwargs['add_time'], ISO_DATE_FMT) - epoc
        else:
            offset = datetime.strptime(kwargs['add_time'], TIME_FMT) - epoc

    log.logger.info("%d files to process", nb_files)
    for filename in file_list:
        log.logger.info("Processing file %d/%d for %s", seq, nb_files, filename)
        if fil.extension(filename).lower() not in ('jpg', 'mp4', 'jpeg', 'gif', 'png', 'mp2', 'mpeg', 'mpeg4', 'mpeg2', 'vob', 'mov'):
            continue
        with ExifToolHelper() as et:
            for data in et.get_metadata(filename):
                creation_date = get_creation_date(data)
                new_date = datetime.strftime(creation_date + offset, EXIF_DATE_FMT)
                log.logger.info("Setting creation date of %s to %s", filename, new_date)
                p = ["-P", "-overwrite_original"]
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
                        # "CreateDate": new_date,
                        # "ModifyDate": new_date,
                        # "DateTimeOriginal": new_date,
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
                    }, params=["-P", "-overwrite_original"])
            for data in et.get_metadata(filename):
                log.logger.debug("MetaData = %s", util.json_fmt(data))
        seq += 1


if __name__ == "__main__":
    main()
