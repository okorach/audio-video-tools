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

# This scripts add metadata to a video file
# Encodable data is
# - Year of video
# - Copyright notice
# - Languages of audio tracks
# - Author of video

from mediatools import log
import mediatools.utilities as util
import utilities.file as fil
import mediatools.videofile as video


def main():
    parser = util.get_common_args('video-metadata', 'Tool to add metadata to media files')
    parser.add_argument('--copyright', required=False, help='Copyright string without (c) sign')
    parser.add_argument('--author', required=False, help='Author of the media file')
    parser.add_argument('--year', required=False, help='Year the media file was produced')
    parser.add_argument('--default_track', required=False, type=int, help='Default track')
    parser.add_argument('--language', required=False, nargs='+',
        help='Languages of tracks, eg "0:fre:Francais sans sous-title" "1:eng:English with music"')
    kwargs = util.parse_media_args(parser)

    inputfile = kwargs.pop('inputfiles')
    if fil.is_video_file(inputfile):
        output = video.VideoFile(inputfile).add_metadata(**kwargs)
        util.generated_file(output)
    else:
        log.logger.error('File %s is not a video file', inputfile)


if __name__ == "__main__":
    main()
