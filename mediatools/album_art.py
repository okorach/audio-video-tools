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

# This script encodes an album art image
# in an MP3 file
# or a set of MP3 files (an album)
# The image is rescaled to 512x512 if too big

import sys
import mediatools.utilities as util
import mediatools.audiofile as audio

DEFAULT_RESCALING = '512x512'


def main():
    util.init('album-art')
    sys.argv.pop(0)
    files = []
    scale = DEFAULT_RESCALING
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == '-g':
            util.set_debug_level(sys.argv.pop(0))
        elif arg == '--scale':
            scale = sys.argv.pop(0)
        else:
            files.append(arg)
    audio.album_art(*files, scale=scale)


if __name__ == "__main__":
    main()
