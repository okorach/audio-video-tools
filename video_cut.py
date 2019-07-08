#!/usr/local/bin/python3

import argparse
import mediatools.videofile as video
import mediatools.utilities as util

parser = util.parse_common_args('Cuts a time window of the input video file')
args = parser.parse_args()
util.set_debug_level(args.debug)

outputfile = video.VideoFile(args.inputfile).cut(args.inputfile, args.start, args.stop, **kwargs)
util.debug(1, 'Generated %s' % outputfile)
