#!/usr/local/bin/python3

import argparse
import mediatools.utilities as util
import mediatools.imagefile as image

parser = argparse.ArgumentParser(description='Image cropper')
parser.add_argument('-i', '--inputfile', required=True, help='Input file to crop')
parser.add_argument('-o', '--outputfile', required=False, help='Output file to create')
parser.add_argument('-n', '--blinds', required=False, default=10, help='Number of blinds')
parser.add_argument('-d', '--direction', required=False, default='vertical', help='Direction to slice')
parser.add_argument('-c', '--color', required=False, default='black', help='Blinds color')
parser.add_argument('-r', '--blinds_ratio', required=False, default=3, help='Size of the blind')
parser.add_argument('-g', '--debug', required=False, default=0, help='Debug level')
args = parser.parse_args()

util.set_debug_level(args.debug)
image.ImageFile(args.inputfile).blindify(int(args.blinds), float(args.blinds_ratio), args.color, args.direction)