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

# This script builds a poster of several input images
# Arranged automatically in n columns m rows
# With configurable padding between images
# And with configurable margin padding
# It requires availability of ffmpeg

import sys
import os
import mediatools.utilities as util
import mediatools.imagefile as image

DEFAULT_RESCALING = '512x512'


def main():
    file_list = []
    dir_list = []
    sys.argv.pop(0)
    kwargs = {'background_color': 'black', 'margin': 5}
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif arg in ('-b', "--background_color"):
            kwargs['background_color'] = sys.argv.pop(0)
        elif arg == "--bottom":
            kwargs['bottom'] = sys.argv.pop(0)
        elif arg == "--top":
            kwargs['top'] = sys.argv.pop(0)
        elif arg == "--left":
            kwargs['left'] = sys.argv.pop(0)
        elif arg == "--right":
            kwargs['right'] = sys.argv.pop(0)
        elif arg in ("--layout"):
            kwargs['layout'] = sys.argv.pop(0)
        elif arg in ('-m', "--margin"):
            kwargs['margin'] = int(sys.argv.pop(0))
        elif arg in ('-r', "--rows"):
            kwargs['rows'] = int(sys.argv.pop(0))
        elif arg in ('-c', "--columns"):
            kwargs['columns'] = int(sys.argv.pop(0))
        elif arg == "--stretch":
            kwargs['stretch'] = True
        elif os.path.isdir(arg):
            dir_list.append(arg)
        else:
            util.logger.info("Adding file %s to poster", arg)
            file_list.append(arg)

    posterfile = image.posterize(*file_list, out_file=None, **kwargs)
    util.generated_file(posterfile)


if __name__ == "__main__":
    main()
