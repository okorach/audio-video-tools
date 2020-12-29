#!python3
#
# media-tools
# Copyright (C) 2019-2020 Olivier Korach
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

# This script encodes an album art image
# in an MP3 file
# or a set of MP3 files (an album)
# The image is rescaled to 512x512 if too big

import sys
import os
import mediatools.utilities as util
import mediatools.audiofile as audio

DEFAULT_RESCALING = '512x512'


def find_image(filelist):
    for file in filelist:
        if util.is_image_file(file):
            return file
    return None


def filelist_album_art(filelist, image_file):
    for file in filelist:
        if util.is_audio_file(file):
            util.logger.info('Encoding album art %s in file %s', image_file, file)
            audio.encode_album_art(file, image_file, scale=DEFAULT_RESCALING)


def dir_album_art(directory):
    filelist = util.file_list(directory)
    dir_album_art_file = find_image(filelist)
    if dir_album_art_file is None:
        util.logger.error("No image file in directory %s", directory)
    else:
        filelist_album_art(filelist, dir_album_art_file)


def main():
    util.logger.setLevel(util.get_logging_level(5))
    file_list = []
    album_art_file = None
    for file_arg in sys.argv:
        if os.path.isdir(file_arg):
            dir_album_art(file_arg)
        elif util.is_image_file(file_arg):
            album_art_file = file_arg
        else:
            file_list.append(file_arg)
    if album_art_file is None:
        util.logger.error("No image file found in %s", str(sys.argv))
    else:
        filelist_album_art(file_list, album_art_file)


if __name__ == "__main__":
    main()
