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

#
# Script to resize an image
# Parameters:
# -i / --inputfile: Image file to resize
# --width: Desired width of the target. If height is not specified, it is calculated to keep image aspect ratio
# --height: Desired height of the target. If width is not specified, it is calculated to keep image aspect ratio
# --size: Desired width x height of the target (format WxH).
# --size parameter is exclusive to --width and/or --height
#
import sys
import mediatools.utilities as util
import mediatools.imagefile as image


def main():
    parser = util.parse_common_args('Image resizer')
    parser.add_argument('--size', required=False,
                        help='New dimensions of the image, size, width or height must be specified')
    parser.add_argument('--width', required=False, help='New width of the image')
    parser.add_argument('--height', required=False, help='New height of the image')
    kwargs = vars(parser.parse_args())

    util.check_environment(kwargs)
    width = kwargs.pop('width', None)
    height = kwargs.pop('height', None)
    if width is None and height is None:
        size = kwargs.pop('size', None)
        if size is None:
            util.logger.error("You must specify either size, or width or height")
            sys.exit(1)
        width, height = size.split("x")

    newfile = image.ImageFile(kwargs.pop('inputfile')).resize(width, height)
    util.logger.info("Generated %s", newfile)


if __name__ == "__main__":
    main()
