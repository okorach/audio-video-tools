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

"""
This scripts adds a shaky effect to an image
Effect can be horizontal or vertical
Arguments: -c <color> -r <ratio> -n <slices> -d <direction>
"""

from mediatools import log
import mediatools.utilities as util
import mediatools.imagefile as image


def main():
    parser = util.get_common_args("image-shake", "Image shake effect")
    parser.add_argument("-n", "--slices", required=False, type=int, default=10, help="Number of slices")
    parser.add_argument("-d", "--direction", required=False, default="vertical", help="Direction to slice")
    parser.add_argument("-c", "--color", required=False, default="black", help="Blinds color")
    parser.add_argument("-r", "--shake_ratio", required=False, type=float, default=3.0, help="Size of the shake")
    kwargs = util.parse_media_args(parser)

    output = image.ImageFile(kwargs.pop("inputfiles")[0]).shake(kwargs["slices"], kwargs["shake_ratio"], kwargs["color"], kwargs["direction"])
    log.logger.info("Generated %s", output)
    print("Generated %s", output)


if __name__ == "__main__":
    main()
