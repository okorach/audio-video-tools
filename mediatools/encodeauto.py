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

# This script applies the ffmpeg deshake filter on a video file
# to improve image stabilization

import os
import argparse
from mediatools.log import logger
import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fileutil

def main():
    parser = argparse.ArgumentParser(description="Simple encoder")
    parser.add_argument('-i', '--inputfiles', type=str, required=True)
    parser.add_argument('-g', '--debug', required=False)
    parser.add_argument('--nooverwrite', required=False, default=False, action='store_true')
    parser.add_argument('--keepName', required=False, default=False, action='store_true')
    parser.add_argument('--before', nargs='*', required=True)
    parser.add_argument('--after', nargs='*', required=True)
    # parser.add_argument('args', nargs=argparse.REMAINDER)
    kwargs = vars(parser.parse_args())
    util.set_debug_level(kwargs.get('debug', 3))
    inputfile = kwargs.pop("inputfiles")
    filesplit = inputfile.split('.')
    before = " ".join(kwargs.pop("before"))
    after = " ".join(kwargs.pop("after"))
    force = not kwargs.pop("nooverwrite")

    is_original = len(filesplit) >= 3 and filesplit[-2] == "original"
    if is_original:
        del filesplit[-2]
    base = fileutil.basename(inputfile, strip_dir=False)
    ext = fileutil.extension(inputfile)
    logger.info("Input = %s, Base = %s ext = %s", inputfile, base, ext)
    seq = 0
    if not force:
        while os.path.isfile(f'{base}.encode.{seq:02}.{ext}'):
            seq += 1
    outputfile = f'{base}.encode.{seq:02}.{ext}'

    cmd = f'{before} -i "{inputfile}" {after} "{outputfile}"'
    logger.info("COMMAND = %s %s", "ffmpeg", cmd)
    util.run_ffmpeg(params=cmd, duration=video.get_duration(inputfile))

    video.set_creation_date(outputfile, video.get_creation_date(inputfile))
    if not is_original:
        renamed = f'{base}.original.{ext}'
        fileutil.rename(inputfile, renamed, force)
        fileutil.rename(outputfile, inputfile, force)
    else:
        os.rename(outputfile, '.'.join(filesplit))

if __name__ == "__main__":
    main()
