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

'''
This script slows down or accelerate a video
'''

import mediatools.utilities as util
import mediatools.videofile as video


def main():
    parser = util.get_common_args('video-speed', 'Video speed change')
    parser.add_argument('--speed', required=True, help='Speed in the form of 4x (accelerate), 0.1x (slow down)')
    parser.add_argument('--keep_audio', dest='audio', action='store_true', help='Keep audio after speed change')
    parser.set_defaults(audio=False)
    kwargs = util.parse_media_args(parser)

    output = video.speed(filename=kwargs.pop('inputfile'), target_speed=kwargs.pop('speed'), output=kwargs.pop('outputfile', None), **kwargs)
    util.logger.info("Generated %s", output)
    print("Generated %s", output)


if __name__ == "__main__":
    main()
