#!/usr/local/bin/python3

import argparse
import mediatools.utilities as util
import mediatools.imagefile as image

parser = argparse.ArgumentParser(description='Image cropper')
parser.add_argument('-i', '--inputfile', required=True, help='Input file to crop')
parser.add_argument('-o', '--outputfile', required=False, help='Output file to create')
parser.add_argument('-n', '--slices', required=False, default=10, help='Number of slices')
parser.add_argument('-d', '--direction', required=False, default='vertical', help='Direction to slice')
parser.add_argument('-c', '--color', required=False, default='black', help='Blinds color')
parser.add_argument('-r', '--shake_ratio', required=False, default=3, help='Size of the shake')
parser.add_argument('-g', '--debug', required=False, default=0, help='Debug level')
args = parser.parse_args()

util.set_debug_level(args.debug)
image.ImageFile(args.inputfile).shake(int(args.slices), float(args.shake_ratio), args.color, args.direction)