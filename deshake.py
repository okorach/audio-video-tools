#!/usr/local/bin/python3

import argparse
import mediatools.utilities as util
from mediatools.videofile import deshake

def parse_args():
    parser = argparse.ArgumentParser(description='Apply deshake filter')
    parser.add_argument('-i', '--inputfile', required=True, help='Input File or Directory to encode')
    parser.add_argument('-o', '--outputfile', required=False, help='Output file to generate')
    parser.add_argument('-w', '--width', required=True, help='Deshake width')
    parser.add_argument('-x', '--height', required=True, help='Deshake height')
    return parser.parse_args()

args = parse_args()
outputfile = deshake(args.inputfile, int(args.width), int(args.height), args.outputfile)
util.debug(1, 'Generated %s' % outputfile)
