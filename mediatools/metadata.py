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

# This scripts add metadata to a video file
# Encodable data is
# - Year of video
# - Copyright notice
# - Languages of audio tracks
# - Author of video

import mediatools.utilities as util
import mediatools.videofile as video


def main():
    parser = util.parse_common_args('Tool to add metadata to media files')
    parser.add_argument('--copyright', required=False, help='Copyright string without year')
    parser.add_argument('--author', required=False, help='Author of the media file')
    parser.add_argument('--year', required=False, help='Year the media file was produced')
    parser.add_argument('--default_track', required=False, type=int, help='Default track')
    parser.add_argument('--languages', required=False, nargs='+', help='Languages of tracks, eg 0:fre 1:eng')
    parser.add_argument('--titles', required=False, nargs='+',
                        help='Titles of tracks, eg "0:French canadian" "1:English with music"')
    kwargs = vars(parser.parse_args())

    util.check_environment(kwargs)
    inputfile = kwargs.pop('inputfile')
    if util.is_video_file(inputfile):
        metas = {'copyright': kwargs.pop('copyright', None),
                'author': kwargs.pop('author', None),
                'year': kwargs.pop('year', None)
        }
        inputfile = video.VideoFile(inputfile).add_metadata(**metas)
        if 'default_track' in kwargs:
            inputfile = video.VideoFile(inputfile).set_default_track(kwargs['default_track'])
        for opt in ['languages', 'titles']:
            if opt not in kwargs:
                continue
            vals = {}
            for s in kwargs[opt]:
                idx, val = s.split(':')
                vals[idx] = val
            if opt == 'languages':
                inputfile = video.VideoFile(inputfile).set_tracks_language(**vals)
            elif opt == 'titles':
                inputfile = video.VideoFile(inputfile).set_tracks_title(**vals)


if __name__ == "__main__":
    main()
