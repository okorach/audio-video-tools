#!python

import videotools.videofile
import sys

def parse_args():
    parser = argparse.ArgumentParser(
            description='Python wrapper for ffmpeg.')
    parser.add_argument('-i', '--inputfile', required=True,
                           help='File to encode'
                        )
    parser.add_argument('-p', '--profile', required=True,
                           help='Profile to use for encoding'
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

# Remove unset params from the dict
noneparms = vars(args)
parms = dict()
for parm in noneparms:
    if noneparms[parm] is not None:
        parms[parm] = noneparms[parm]
# Add SQ environment
# parms.update(dict(env=sqenv))

videotools.videofile.encode(parms['inputfile'], None, parms['profile'])
