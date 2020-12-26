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

import sys
import mediatools.utilities as util
import mediatools.mediafile as media
import mediatools.videofile as video
import mediatools.version as version


def main():
    files = []
    util.set_logger('video-slideshow')
    resolution = media.Resolution.DEFAULT_VIDEO
    sys.argv.pop(0)
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif arg == "--resolution":
            resolution = sys.argv.pop(0)
        else:
            files.append(arg)
    if len(files) > 0:
        output = video.slideshow(*files, resolution=resolution)
        util.logger.info("slideshow v%s - File %s generated", version.MEDIA_TOOLS_VERSION, output)
    else:
        util.logger.error("No inputs files could be used for slideshow, no slideshow generated")


if __name__ == "__main__":
    main()
