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

# This script build an image composed of
# 2 input images that can be glued
# horizontally or vertically

import sys
from mediatools import log
import mediatools.imagefile as image
import mediatools.utilities as util

USAGE = "image-stack [--direction vertical|horizontal] [--margin <nb_pixels>] \
[--stretch] [-g 0-4] file1 file2 ... filen"


def main():
    files = []
    util.init('image-stack')
    kwargs = {'direction': 'vertical', 'margin': 0, 'stretch': True, 'background_color': 'black'}
    sys.argv.pop(0)
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == '-g':
            util.set_debug_level(sys.argv.pop(0))
        elif arg in ('-d', '--direction'):
            kwargs['direction'] = sys.argv.pop(0)
        elif arg in ('-b', '--background_color'):
            kwargs['background_color'] = sys.argv.pop(0)
        elif arg in ('-m', '--margin'):
            kwargs['margin'] = sys.argv.pop(0)
        elif arg == '--stretch':
            kwargs['stretch'] = True
        elif arg in ('-h', '--help'):
            print("Usage: {}".format(USAGE))
            sys.exit(0)
        else:
            files.append(arg)

    if len(files) > 0:
        output = image.stack(*files, out_file=None, **kwargs)
        log.logger.info("File %s generated", output)
        print('Generated', output)
    else:
        log.logger.error("No inputs files could be used for slideshow, no slideshow generated")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
