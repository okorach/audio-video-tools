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

# This script applies the ffmpeg deshake filter on a video file
# to improve image stabilization

import re
import mediatools.utilities as util
import mediatools.videofile as video


def main():
    parser = util.get_common_args('video-stabilize', 'Apply deshake filter')
    parser = video.add_video_args(parser)
    parser.add_argument('--rx', required=False, type=int, default=64, choices=range(65),
        help='Deshake rx', metavar="[0-64]")
    parser.add_argument('--ry', required=False, type=int, default=64, choices=range(65),
        help='Deshake ry', metavar="[0-64]")
    parser.add_argument('--crop', dest='crop', action='store_true', help='Crop video after stabilization')
    parser.add_argument('--nocrop', dest='crop', action='store_false', help='Do not crop video after stabilization')
    parser.set_defaults(crop=True)
    kwargs = util.parse_media_args(parser=)

    rx = kwargs.pop('rx')
    ry = kwargs.pop('ry')
    if kwargs['timeranges'] is not None:
        kwargs['ss'], kwargs['to'] = kwargs['timeranges'].split(',')[0].split('-')
    outputfile = video.VideoFile(kwargs['inputfile']).deshake(rx=rx, ry=ry,
        out_file=kwargs.get('outputfile', None), **kwargs)
    print('Generated {}'.format(outputfile))


if __name__ == "__main__":
    main()
