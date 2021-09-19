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

# This script creates a venetian blinds effect on an image
# ie interweaves slices of images and slices of black (or white)

from mediatools import log
import mediatools.utilities as util
import mediatools.imagefile as image


def main():
    parser = util.get_common_args('image-blinds', 'Creates a window blinds effect on an image')
    parser.add_argument('-n', '--blinds', required=False, default=10, help='Number of blinds')
    parser.add_argument('-d', '--direction', required=False, default='vertical', help='Direction to slice')
    parser.add_argument('-c', '--background_color', required=False, default='black', help='Blinds color')
    parser.add_argument('-b', '--blinds_size', required=False, default="3%", help='Size of the blind like 2%')
    kwargs = util.parse_media_args(parser)
    output = image.ImageFile(kwargs.pop('inputfile')).blindify(**kwargs)
    log.logger.info("Generated file %s", output)
    print("Generated file {}".format(output))


if __name__ == "__main__":
    main()
