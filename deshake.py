#!/Library/Frameworks/Python.framework/Versions/3.6/bin/python3

from videotools.videofile import deshake
from videotools.filetools import debug
import sys
import os
import re
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Apply deshake filter')
    parser.add_argument('-i', '--inputfile', required=True, help='Input File or Directory to encode')
    parser.add_argument('-o', '--outputfile', required=False, help='Output file to generate')
    parser.add_argument('-w', '--width', required=True, help='Deshake width')
    parser.add_argument('-x', '--height', required=True, help='Deshake height')
    args = parser.parse_args()
    return args

args = parse_args()
outputfile = deshake(args.inputfile, int(args.width), int(args.height), args.outputfile)
debug(1, 'Generated %s' % outputfile)
