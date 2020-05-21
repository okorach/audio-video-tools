#!/usr/local/bin/python3

'''
This script cuts a video
It will be improved soon
'''

import argparse
import mediatools.videofile as video
import mediatools.utilities as util

parser = util.parse_common_args('Cuts a time window of the input video file')
kwargs = vars(parser.parse_args())
util.check_environment(kwargs)
start = kwargs.pop('start', None)
stop = kwargs.pop('stop', None)
ifile = kwargs.pop('inputfile')
outputfile = video.VideoFile(ifile).cut(start, stop, **kwargs)
util.debug(1, 'Generated %s' % outputfile)
