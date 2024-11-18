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

'''
This script slows down or accelerate a video
'''

import sys
import re
from mediatools import log
import mediatools.options as opt
import mediatools.utilities as util
import mediatools.videofile as video

ALLOWED_SPEEDS = ("10%", "12.5%", "25%", "50%", "100%", "150%", "200%", "250%", "300%", "400%", "500%",
            "600%", "700%", "800%", "1000%", "1500%", "2000%", "3000%", "4000%", "5000%", "6000%", "8000%", "10000%")


def main():
    parser = util.get_common_args('video-speed', 'Video speed change')
    parser.add_argument('-p', '--profile', required=False, help='Profile to use for encoding')
    parser.add_argument('--speed', required=True, help='Speed in the form of 4x (accelerate), 0.1x (slow down)')
    parser.add_argument('-k', '--keep_audio', required=False, dest=opt.Option.MUTE, action='store_false',
        default=True, help='Keep audio track after speed change')
    parser.set_defaults(audio=False)
    kwargs = util.parse_media_args(parser)
    speed = kwargs.pop('speed')
    kwargs['hw_accel'] = 'off'
    if re.match(r".*%$", speed) and speed not in ALLOWED_SPEEDS:
        log.logger.critical("Speed value %s is not allowed, it must be less than 100%% or one of %s",
            speed, ', '.join(ALLOWED_SPEEDS))
        sys.exit(1)

    output = video.speed(filename=kwargs.pop('inputfiles'), target_speed=speed,
        output=kwargs.pop('outputfile', None), **kwargs)
    util.generated_file(output)


if __name__ == "__main__":
    main()
