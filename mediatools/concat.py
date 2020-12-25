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

# This script concatenate 2 video files
# They should have the same video and audio codecs and bitrates

import sys
import mediatools.utilities as util
import mediatools.videofile as video


def main():
    util.set_debug_level(2)

    sys.argv.pop(0)
    target_file = sys.argv.pop()

    filelist = []
    for file in sys.argv:
        filelist.append(file)

    video.concat(target_file, filelist)


if __name__ == "__main__":
    main()
