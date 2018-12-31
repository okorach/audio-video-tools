#!python3

import sys
import os
import re
import argparse
import mediatools.videofile as video
import mediatools.utilities as util

parser = argparse.ArgumentParser(description='Rescale image dimensions of a file or directory')
parser.add_argument('-i', '--inputfile', required=True, help='Input File or Directory to encode')
parser.add_argument('-o', '--outputfile', required=False, help='Output file to generate')
parser.add_argument('-s', '--scale', required=True, help='Dimensions to rescale widthxheight')
parser.add_argument('-g', '--debug', required=False, default=0, help='Debug level')

args = parser.parse_args()
util.set_debug_level(args.debug)
width, height = args.scale.split("x")
outputfile = video.rescale(args.inputfile, width, height, args.outputfile)

print('Generated', outputfile)
