#!/usr/local/bin/python3

'''
This script cuts a video
It will be improved soon
'''

import argparse
import mediatools.videofile as video
import mediatools.utilities as util


def main():
    parser = util.parse_common_args('Cuts a time window of the input video file')
    kwargs = vars(parser.parse_args())
    util.check_environment(kwargs)
    start = kwargs.pop('start', None)
    stop = kwargs.pop('stop', None)
    ifile = kwargs.pop('inputfile')
    outputfile = video.VideoFile(ifile).cut(start=start, stop=stop, fade=2, **kwargs)
    util.logger.info('Generated file %s', outputfile)


if __name__ == "__main__":
    main()