#!/usr/local/bin/python3

import sys
import os
import re
import argparse
import mediatools.imagefile as image
import mediatools.utilities as util

parser = util.parse_common_args('Rescale image dimensions of a file or directory')
parser.add_argument('-s', '--scale', required=True, help='Dimensions to rescale widthxheight')

args = parser.parse_args()
util.check_environment(vars(args))
width, height = args.scale.split("x")
outputfile = image.rescale(args.inputfile, width, height, args.outputfile)

print('Generated', outputfile)
