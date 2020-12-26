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


def parse_args():
    parser = util.parse_common_args(desc='Apply deshake filter')
    parser = video.add_video_args(parser)
    parser.add_argument('--width', required=True, help='Deshake width')
    parser.add_argument('--height', required=True, help='Deshake height')
    parser.add_argument('--nocrop', required=False, help='Do not crop video after deshaking')
    return parser.parse_args()


def main():
    args = parse_args()
    kwargs = vars(args)
    util.check_environment(kwargs)
    kwargs = util.cleanup_options(kwargs)
    del kwargs['width']
    del kwargs['height']
    if args.timeranges is not None:
        for video_range in re.split(',', args.timeranges):
            kwargs['ss'], kwargs['to'] = re.split('-', video_range)
    outputfile = video.deshake(args.inputfile, int(args.width), int(args.height), args.outputfile, **kwargs)
    util.logger.info('Generated %s', outputfile)


if __name__ == "__main__":
    main()
