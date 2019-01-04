#!python3

import argparse
import mediatools.videofile as video
import mediatools.utilities as util

parser = util.parse_common_args('Crops a region of the input video file')
parser.add_argument('--box', required=True, help='Video box eg 320x200')
parser.add_argument('--top', required=True, help='Video top origin')
parser.add_argument('--left', required=True, help='Video left origin')
args = parser.parse_args()
util.set_debug_level(args.debug)

width, height = args.box.split("x")
kwargs = vars(args).copy()
for key in ['inputfile', 'outputfile', 'box', 'debug', 'left', 'top']:
    del kwargs[key]

outputfile = video.crop(args.inputfile, int(width), int(height), int(args.top), int(args.left), \
    args.outputfile, **kwargs)
util.debug(1, 'Generated %s' % outputfile)
