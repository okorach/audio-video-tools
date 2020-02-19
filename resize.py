#!/usr/local/bin/python3
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
import argparse
import mediatools.utilities as util
import mediatools.imagefile as image

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
