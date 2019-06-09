#!/usr/local/bin/python3

import argparse
import mediatools.utilities as util
import mediatools.imagefile as image

parser = argparse.ArgumentParser(description='Image cropper')
parser.add_argument('-i', '--inputfile', required=True, help='Input file to crop')
parser.add_argument('-o', '--outputfile', required=False, help='Output file to create')
parser.add_argument('--align', required=False, default='center', help='How to crop')
parser.add_argument('-g', '--debug', required=False, default=0, help='Debug level')
args = parser.parse_args()

util.set_debug_level(args.debug)
image.ImageFile(args.inputfile).crop_square(args.align)