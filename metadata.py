#!/usr/local/bin/python3

import argparse
import mediatools.utilities as util
import mediatools.videofile as video

parser = util.parse_common_args('Tool to add metadata to media files')
parser.add_argument('--copyright', required=False, help='Copyright string without year')
parser.add_argument('--author', required=False, help='Author of the media file')
parser.add_argument('--year', required=False, help='Year the media file was produced')
kwargs = vars(parser.parse_args())

util.check_environment(kwargs)
inputfile = kwargs.pop('inputfile')
if util.is_video_file(inputfile):
    metas = {'copyright': kwargs.pop('copyright', None), \
             'author': kwargs.pop('author', None), \
             'year': kwargs.pop('year', None)
            }
    video.VideoFile(inputfile).add_metadata(**metas)
