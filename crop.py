#!/Library/Frameworks/Python.framework/Versions/3.6/bin/python3

import argparse
from mediatools.videofile import crop
from mediatools.utilities import debug, set_debug_level

def parse_args():
    parser = argparse.ArgumentParser(description='Apply deshake filter')
    parser.add_argument('-i', '--inputfile', required=True, help='Input File or Directory to encode')
    parser.add_argument('-o', '--outputfile', required=False, help='Output file to generate')
    parser.add_argument('-g', '--debug', required=False, help='util.debug level')
    parser.add_argument('-b', '--box', required=True, help='Video box')
    parser.add_argument('-t', '--top', required=True, help='Video top origin')
    parser.add_argument('-l', '--left', required=True, help='Video left origin')
    return parser.parse_args()

args = parse_args()
set_debug_level(args.debug)

width, height = args.box.split("x")
outputfile = crop(args.inputfile, int(width), int(height), int(args.top), int(args.left), args.outputfile)
debug(1, 'Generated %s' % outputfile)
