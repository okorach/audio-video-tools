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
This script cuts a video
It will be improved soon
'''

import mediatools.videofile as video
import mediatools.utilities as util


def main():
    parser = util.get_common_args('video-cut', 'Cuts a time window of the input video file')
    parser = video.add_video_args(parser)
    kwargs = util.parse_common_args(parser)
    ranges = kwargs.get('timeranges', None)
    if ranges is None:
        util.logger.error('--timeranges option is mandatory, type video-cut -h for more details')
    else:
        outputfile = video.VideoFile(kwargs.pop('inputfile')).cut(start=kwargs['start'], stop=kwargs['stop'])
        print('Generated file {}'.format(outputfile))


if __name__ == "__main__":
    main()
