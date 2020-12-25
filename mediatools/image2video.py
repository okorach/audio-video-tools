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

import argparse
import mediatools.utilities as util
import mediatools.imagefile as image
import mediatools.mediafile as media

def main():
    parser = util.parse_common_args('image2video')
    parser.add_argument('-e', '--effect', required=False, default="zoom", help='Effect to generate')
    parser.add_argument('-z', '--zoom_effect', required=False, default=1.3, help='Zoom level for zoom in/out')
    parser.add_argument('--panorama_effect', required=False, default="left", help='Type of panorama')
    parser.add_argument('--duration', required=False, default=5, help='Duration of video')
    parser.add_argument('--direction', required=False, default="left", help='Direction of the panorama')
    kwargs = util.remove_nones(vars(parser.parse_args()))

    util.check_environment(kwargs)
    inputfile = kwargs.pop('inputfile')
    resolution = kwargs.get('framesize', media.Resolution.DEFAULT_VIDEO)

    if kwargs['effect'] == "panorama":
        effect = [float(x) for x in kwargs.get('panorama_effect', "0.2,0.8,0.6,0.4").split(",")]
        image.ImageFile(inputfile).panorama(resolution=resolution, duration=kwargs['duration'],
            effect=effect)
    else:
        effect = [float(x) for x in kwargs.get('zoom_effect', "100,130").split(",")]
        image.ImageFile(inputfile).zoom(resolution=resolution, duration=kwargs['duration'],
            effect=effect)


if __name__ == "__main__":
    main()
