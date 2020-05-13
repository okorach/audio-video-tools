#!/usr/local/bin/python3

# This script creates a venetian blinds effect on an image
# ie interweaves slices of images and slices of black (or white)

import argparse
import mediatools.utilities as util
import mediatools.imagefile as image

parser = util.parse_common_args('Image cropper')
parser.add_argument('-n', '--blinds', required=False, default=10, help='Number of blinds')
parser.add_argument('-d', '--direction', required=False, default='vertical', help='Direction to slice')
parser.add_argument('-c', '--background_color', required=False, default='black', help='Blinds color')
parser.add_argument('-r', '--blinds_ratio', required=False, default=3, help='Size of the blind')
kwargs = vars(parser.parse_args())

util.check_environment(kwargs)
inputfile = kwargs.pop('inputfile')
image.ImageFile(inputfile).blindify(**kwargs)
