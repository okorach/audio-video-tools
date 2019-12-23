#!/usr/local/bin/python3

import argparse
import mediatools.imagefile as image
import mediatools.utilities as util

parser = util.parse_common_args('Sticks 2 image together')
parser.add_argument('-i2', '--inputfile2', required=True, help='Input File 2')
parser.add_argument('-d', '--direction', required=False, default='vertical', \
    help='Stacking direction (horizontal or vertical)')

args = parser.parse_args()
util.check_environment(vars(args))

outputfile = image.stack(args.inputfile, args.inputfile2, args.direction, args.outputfile)

print('Generated', outputfile)
