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

# This script crops an image file

import mediatools.utilities as util
import mediatools.imagefile as image


def main():
    parser = util.get_common_args('image-crop-ratio', 'Image cropper')
    parser.add_argument('--align', required=False, default='center', help='How to crop')
    parser.add_argument('--ratio', required=True, help='W/H ratio of picture like 2, 1.5')
    kwargs = util.parse_media_args(parser)
    image.ImageFile(kwargs['inputfile']).crop_any(kwargs['ratio'], kwargs['align'])


if __name__ == "__main__":
    main()
