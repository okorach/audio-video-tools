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

import argparse
from mediatools import log
import mediatools.file as fil
import mediatools.videofile as video
import mediatools.utilities as util


def main():
    util.init('video-mux')
    parser = argparse.ArgumentParser(description='Stacks images vertically or horizontally')
    parser.add_argument('-i','--inputfile', nargs='+', help='List of files to mux', required=True)
    parser.add_argument('-o','--outputfile', help='Output file to generate', required=False)
    parser.add_argument('-g', '--debug', required=False, type=int, help='Debug level')
    kwargs = util.parse_media_args(parser)

    afiles = kwargs.pop('inputfile')
    for f in afiles.copy():
        if fil.is_video_file(f):
            vfile = f
            afiles.remove(f)
            break
    log.logger.info("Muxing audio files %s in video file %s", str(afiles), vfile)
    videofile = video.VideoFile(vfile)
    output = videofile.add_audio_tracks(*afiles, out_file=kwargs.pop('outputfile'))
    util.generated_file(output)


if __name__ == "__main__":
    main()
