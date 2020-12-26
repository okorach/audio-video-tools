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

# This script build an image composed of
# 2 input images that can be glued
# horizontally or vertically

import mediatools.imagefile as image
import mediatools.utilities as util


def main():
    parser = util.parse_common_args('Sticks 2 image together')
    parser.add_argument('-i2', '--inputfile2', required=True, help='Input File 2')
    parser.add_argument('-d', '--direction', required=False, default='vertical',
                        help='Stacking direction (horizontal or vertical)')

    args = parser.parse_args()
    util.check_environment(vars(args))

    outputfile = image.stack(args.inputfile, args.inputfile2, args.direction, args.outputfile)

    print('Generated', outputfile)


if __name__ == "__main__":
    main()
