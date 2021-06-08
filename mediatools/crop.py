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

# This scripts crops a region of a video file
# You have to pass:
# --box <width>x<height> : The size of the video to crop
# --top <y>/ --left <x>: Coordinates of the top left corner of the video crop

import mediatools.log as log
import mediatools.creator as creator
import mediatools.videofile as video
import mediatools.utilities as util


def main():
    parser = util.get_common_args('video-crop', 'Crops a region of the input video file')
    parser = video.add_video_args(parser)
    parser.add_argument('--box', required=True, help='Video box eg 320x200')
    parser.add_argument('--position', required=False, help='Crop video position (from top-left to bottom-right)')
    parser.add_argument('--top', required=False, help='Video top origin')
    parser.add_argument('--left', required=False, help='Video left origin')
    kwargs = util.parse_media_args(parser)

    kwargs['width'], kwargs['height'] = kwargs['box'].split("x", maxsplit=2)
    log.logger.debug("KW=%s", str(kwargs))
    outputfile = creator.file(kwargs['inputfile']).crop(out_file=kwargs.get('outputfile', None), **kwargs)
    log.logger.info('Generated %s', outputfile)
    print("Generated {}".format(outputfile))


if __name__ == "__main__":
    main()
