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

# This script builds a poster of several input images
# Arranged automatically in n columns m rows
# With configurable padding between images
# And with configurable margin padding
# It requires availability of ffmpeg

import argparse
import mediatools.utilities as util
import mediatools.imagefile as image

USAGE = "image-poster [--layout <rows>x<cols>] [--margin <nb_pixels>] \
[--background_color [black|white]] [--stretch] [-g 0-4] file1 file2 ... filen"


def main():
    file_list = []
    util.init('image-poster')
    parser = argparse.ArgumentParser(description='Creates a mosaic of images for posters')
    parser.add_argument('-i', '--inputfiles', nargs='+', help='List of files to posterize', required=True)
    parser.add_argument('-o', '--outputfile', help='Output file to generate', required=False)
    parser.add_argument('-g', '--debug', required=False, type=int, help='Debug level')
    parser.add_argument('-b', '--background_color', required=False, choices=['black', 'white'],
        default='black', help='Background color of frame')
    parser.add_argument('-m', '--margin', required=False, default=0, help='Width of margin')
    parser.add_argument('-l', '--layout', required=False, help='Layout of pictures cols x rows')
    parser.add_argument('--stretch', required=False, dest='stretch', action='store_true',
        default=False, help='Stretch images so that they have the same width and height')
    kwargs = util.parse_media_args(parser)
    file_list = kwargs['inputfiles']

    posterfile = image.posterize(*file_list, out_file=kwargs.get('outputfile', None), **kwargs)
    util.generated_file(posterfile)


if __name__ == "__main__":
    main()
