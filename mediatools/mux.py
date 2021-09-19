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

# This script multiplexes an extra audio track
# in a video file with already one audio track

import sys
from mediatools import log
import mediatools.file as fil
import mediatools.videofile as video
import mediatools.utilities as util


def main():
    util.init('video-mux')
    sys.argv.pop(0)
    afiles = []
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == '-g':
            util.set_debug_level(sys.argv.pop(0))
        elif fil.is_video_file(arg):
            vfile = arg
            log.logger.info("Video file %s will be muxed", arg)
        elif fil.is_audio_file(arg):
            log.logger.info("Audio file %s will be muxed", arg)
            afiles.append(arg)

    videofile = video.VideoFile(vfile)
    videofile.add_audio_tracks(*afiles)


if __name__ == "__main__":
    main()
