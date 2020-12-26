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

# This scripts crops a region of a video file
# You have to pass:
# --box <width>x<height> : The size of the video to crop
# --top <y>/ --left <x>: Coordinates of the top left corner of the video crop

import mediatools.videofile as video
import mediatools.utilities as util
import mediatools.options as opt


def main():
    parser = util.parse_common_args('Crops a region of the input video file')
    parser = video.add_video_args(parser)
    parser.add_argument('--box', required=True, help='Video box eg 320x200')
    parser.add_argument('--center', required=False, help='Crop video on center of origin video')
    parser.add_argument('--top', required=False, help='Video top origin')
    parser.add_argument('--left', required=False, help='Video left origin')
    args = parser.parse_args()
    kwargs = vars(args).copy()
    util.check_environment(kwargs)

    if args.box == '720p':
        args.box = '1280x720'
    elif args.box == '540p':
        args.box = '960x540'
    elif args.box == '1080p':
        args.box = '1920x1080'

    if args.timeranges is not None:
        (kwargs[opt.media.START], kwargs[opt.media.STOP]) = args.timeranges.split('-')

    width, height = [int(x) for x in args.box.split("x")]
    file_o = video.VideoFile(args.inputfile)
    if args.center is not None and args.center == "true":
        i_w, i_h = file_o.get_dimensions()
        left = (i_w - width) // 2
        top = (i_h - height) // 2
    else:
        top = int(args.top)
        left = int(args.left)

    # Remove the explicitly passed arguments
    for key in ['inputfile', 'outputfile', 'box', 'left', 'top', 'center']:
        kwargs.pop(key, None)

    outputfile = video.VideoFile(args.inputfile).crop(width, height, top, left,
        args.outputfile, **kwargs)
    util.logger.info('Generated %s', outputfile)


if __name__ == "__main__":
    main()
