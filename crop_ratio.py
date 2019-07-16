#!/usr/local/bin/python3

import argparse
import mediatools.utilities as util
import mediatools.imagefile as image

parser = argparse.ArgumentParser(description='Image cropper')
parser = util.parse_common_args('Image cropper')
parser.add_argument('--align', required=False, default='center', help='How to crop')
parser.add_argument('--ratio', required=True, help='W/H ratio of picture like 2, 1.5')
args = parser.parse_args()

util.set_debug_level(args.debug)
image.ImageFile(args.inputfile).crop_any(args.ratio, args.align)
