#!/usr/local/bin/python3

import argparse
import mediatools.videofile as video
import mediatools.utilities as util

parser = util.parse_common_args('Cuts a time window of the input video file')
kwargs = vars(parser.parse_args())
util.set_debug_level(dict.pop(kwargs, 'debug'))
start = dict.pop(kwargs, 'start')
stop = dict.pop(kwargs, 'stop')
ifile = dict.pop(kwargs, 'inputfile')
outputfile = video.VideoFile(ifile).cut(start, stop, **kwargs)
util.debug(1, 'Generated %s' % outputfile)
