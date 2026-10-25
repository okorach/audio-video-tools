#
# media-tools
# Copyright (C) 2019-2026 Olivier Korach
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

"""Tool that stacks images vertically or horizontally"""

import sys
import argparse
import mediatools.imagefile as image
import mediatools.utilities as util
import utilities.file as fil

USAGE = "image-stack [--direction vertical|horizontal] [--margin <nb_pixels>] \
[--stretch] [-g 0-4] file1 file2 ... filen"


def main() -> None:
    """Stacks images vertically or horizontally in a single image"""
    files = []
    util.init("image-stack")
    parser = argparse.ArgumentParser(description="Stacks images vertically or horizontally")
    util.add_input_args(parser, "List of files to stack")
    util.add_output_args(parser, "Output file to generate")
    util.add_verbosity_arg(parser)
    util.add_hw_accel_arg(parser)
    parser.add_argument("-d", "--direction", required=False, choices=["vertical", "horizontal"], default="vertical", help="How to stack images")
    parser.add_argument("-b", "--background_color", required=False, choices=["black", "white"], default="black", help="Background color of frame")
    parser.add_argument("-m", "--margin", required=False, default=0, help="Width of frame")
    parser.add_argument(
        "--stretch",
        required=False,
        dest="stretch",
        action="store_true",
        default=False,
        help="Stretch images so that they have the same width or height",
    )
    kwargs = util.parse_media_args(parser, input_type=fil.FileType.IMAGE_FILE)
    files = kwargs[util.INPUT_FILES]
    output = image.stack(*files, out_file=kwargs.get(util.OUTPUT_FILE, None), **kwargs)
    util.generated_file(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
