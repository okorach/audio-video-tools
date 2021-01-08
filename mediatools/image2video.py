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

import mediatools.utilities as util
import mediatools.imagefile as image
import mediatools.resolution as res


def main():
    parser = util.get_common_args('image2video', 'Converts an image to a video')
    parser.add_argument('-e', '--effect', required=True, default="zoom", help='Effect to generate')
    parser.add_argument('--bounds', required=False, help='bounds of the panorama or zoom')
    parser.add_argument('--speed', required=False, help='Panorama or zoom speed')
    parser.add_argument('--vspeed', required=False, default=0, help='Panorama or zoom vertical speed')
    parser.add_argument('--duration', required=False, help='Panorama or zoom duration')
    kwargs = util.parse_media_args(parser)

    inputfile = kwargs.pop('inputfile')
    resolution = kwargs.get('size', res.Resolution.DEFAULT_VIDEO)

    effect = None
    if kwargs.get('bounds', None) is not None:
        effect = [float(x) for x in kwargs['bounds'].split(",")]

    if kwargs['effect'] == 'panorama':
        kwargs.pop('effect')
        output = image.ImageFile(inputfile).panorama(resolution=resolution, effect=effect, **kwargs)
    else:
        kwargs.pop('effect')
        output = image.ImageFile(inputfile).zoom(resolution=resolution, effect=effect, **kwargs)
    util.generated_file(output)


if __name__ == "__main__":
    main()
