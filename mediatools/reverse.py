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

import argparse
import mediatools.utilities as util
import mediatools.options as opt
import mediatools.videofile as video


def main():
    util.init('video-reverse')
    parser = argparse.ArgumentParser(description='Reverse a video')
    parser.add_argument('-i', '--inputfile', help='Video file to reverse', required=True)
    parser.add_argument('-o', '--outputfile', help='Output file to generate', required=False)
    parser.add_argument('-g', '--debug', required=False, type=int, help='Debug level')
    parser.add_argument('-k', '--keep_audio', required=False, dest=opt.Option.MUTE, action='store_false',
        default=True, help='Keep audio track after reverse')
    parser.add_argument('--hw_accel', required=False, dest='hw_accel', action='store_true',
        default=False, help='Enable hardware (GPU) acceleration')
    kwargs = util.parse_media_args(parser)
    output = video.reverse(kwargs.pop('inputfile'), kwargs.get('outputfile', None), **kwargs)
    util.generated_file(output)


if __name__ == "__main__":
    main()
