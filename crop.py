#!/usr/local/bin/python3
# This scripts crops a region of a video file
# You have to pass:
# --box <width>x<height> : The size of the video to crop
# --top <y>/ --left <x>: Coordinates of the top left corner of the video crop


import argparse
import mediatools.videofile as video
import mediatools.utilities as util

parser = util.parse_common_args('Crops a region of the input video file')
parser = video.add_video_args(parser)
parser.add_argument('--box', required=True, help='Video box eg 320x200')
parser.add_argument('--center', required=False, help='Crop video on center of origin video')
parser.add_argument('--top', required=False, help='Video top origin')
parser.add_argument('--left', required=False, help='Video left origin')
args = parser.parse_args()
kwargs = vars(args).copy()
util.check_environment(kwargs)

width, height = util.int_split(args.box, "x")
file_o = video.VideoFile(args.inputfile)
if args.center is not None and args.center == "true":
    i_w, i_h = file_o.get_dimensions()
    left = (i_w - width)/2
    top = (i_h - height)/2
else:
    top = int(args.top)
    left = int(args.left)

# Remove the explicitly passed arguments
for key in ['inputfile', 'outputfile', 'box', 'left', 'top', 'center']:
    kwargs.pop(key, None)

outputfile = video.VideoFile(args.inputfile).crop(int(width), int(height), int(args.top), int(args.left), \
    args.outputfile, **kwargs)
util.logger.info('Generated %s', outputfile)
