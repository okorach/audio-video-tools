#!python3

import videotools.videofile
import sys
import os
import re

def parse_args():
    parser = argparse.ArgumentParser(
            description='Python wrapper for ffmpeg.')
    parser.add_argument('-i', '--inputfile', required=True,
                           help='Input File or Directory to encode'
                        )
    parser.add_argument('-o', '--outputfile', required=False,
                           help='Output file to generate'
                        )
    parser.add_argument('-s', '--scale', required=True,
                           help='Dimensions to rescale widthxheight'
                        )
    args = parser.parse_args()

    return args

try:
    import argparse
except ImportError:
    if sys.version_info < (2, 7, 0):
        print("Error:")
        print("You are running an old version of python. Two options to fix the problem")
        print("  Option 1: Upgrade to python version >= 2.7")
        print("  Option 2: Install argparse library for the current python version")
        print("            See: https://pypi.python.org/pypi/argparse")

args = parse_args()
width, height = args.scale.split("x")
outputfile = videotools.videofile.rescale(args.inputfile, width, height)

print('Generated', outputfile)
