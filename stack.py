#!/usr/local/bin/python3

import sys
import os
import re
import argparse
import mediatools.imagefile as image
import mediatools.utilities as util

parser = argparse.ArgumentParser(description='Sticks 2 image together')
parser.add_argument('-i1', '--inputfile1', required=True, help='Input File 1')
parser.add_argument('-i2', '--inputfile2', required=True, help='Input File 2')
parser.add_argument('-o', '--outputfile', required=False, help='Output file to generate')
parser.add_argument('-d', '--direction', required=False, default='vertical', \
    help='Stacking direction (horizontal or vertical)')
parser.add_argument('-g', '--debug', required=False, default=0, help='Debug level')

args = parser.parse_args()
util.set_debug_level(args.debug)

outputfile = image.stack(args.inputfile1, args.inputfile2, args.direction, args.outputfile)

print('Generated', outputfile)
