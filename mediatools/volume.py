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
    parser = util.get_common_args('media-volume', 'Change volume of a video or audio file')
    parser.add_argument('--volume', required=True, help='Change volume like 4x (relative change) or 6dB (absolute)')
    kwargs = util.parse_media_args(parser)

    output = video.volume(kwargs.pop('inputfile'), kwargs.pop('volume'), kwargs.get('outputfile', None))
    util.generated_file(output)



if __name__ == "__main__":
    main()
