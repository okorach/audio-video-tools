#!python3

import mediatools.videofile
import argparse
import sys
import os
import re

def parse_args():
    parser = argparse.ArgumentParser(description='Rescale image dimensions of a file or directory')
    parser.add_argument('-i', '--inputfile', required=True, help='Input File or Directory to encode')
    parser.add_argument('-o', '--outputfile', required=False, help='Output file to generate')
    parser.add_argument('-s', '--scale', required=True, help='Dimensions to rescale widthxheight')
    args = parser.parse_args()
    return args

args = parse_args()
width, height = args.scale.split("x")
outputfile = mediatools.videofile.rescale(args.inputfile, width, height, args.outputfile)

print('Generated', outputfile)
