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

# This script build an image composed of
# 2 input images that can be glued
# horizontally or vertically

import sys
import mediatools.mediafile as media
import mediatools.imagefile as image
import mediatools.utilities as util


def main():
    files = []
    util.set_logger('image-stack')
    sys.argv.pop(0)
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif arg == "--direction":
            direction = sys.argv.pop(0)
        else:
            files.append(arg)
    # files = util.file_list(*files, file_type=util.MediaType.IMAGE_FILE)

    if len(files) > 0:
        output = image.stack(*files, direction=direction)
        util.logger.info("File %s generated", output)
        print('Generated', output)
    else:
        util.logger.error("No inputs files could be used for slideshow, no slideshow generated")
        exit(1)
    exit(0)


if __name__ == "__main__":
    main()
