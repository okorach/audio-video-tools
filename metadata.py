#!/usr/local/bin/python3

# This scripts add metadata to a video file
# Encodable data is
# - Year of video
# - Copyright notice
# - Languages of audio tracks
# - Author of video

import argparse
import mediatools.utilities as util
import mediatools.videofile as video

parser = util.parse_common_args('Tool to add metadata to media files')
parser.add_argument('--copyright', required=False, help='Copyright string without year')
parser.add_argument('--author', required=False, help='Author of the media file')
parser.add_argument('--year', required=False, help='Year the media file was produced')
parser.add_argument('--default_track', required=False, type=int, help='Default track')
parser.add_argument('--languages', required=False, nargs='+', help='Languages of tracks, eg 0:fre 1:eng')
parser.add_argument('--titles', required=False, nargs='+', \
                    help='Titles of tracks, eg "0:French canadian" "1:English with music"')
kwargs = vars(parser.parse_args())

util.check_environment(kwargs)
inputfile = kwargs.pop('inputfile')
if util.is_video_file(inputfile):
    metas = {'copyright': kwargs.pop('copyright', None), \
             'author': kwargs.pop('author', None), \
             'year': kwargs.pop('year', None)
            }
    inputfile = video.VideoFile(inputfile).add_metadata(**metas)
    if 'default_track' in kwargs:
        inputfile = video.VideoFile(inputfile).set_default_track(kwargs['default_track'])
    for opt in ['languages', 'titles']:
        if opt not in kwargs:
            continue
        vals = {}
        for s in kwargs[opt]:
            idx, val = s.split(':')
            vals[idx] = val
        if opt == 'languages':
            inputfile = video.VideoFile(inputfile).set_tracks_language(**vals)
        elif opt == 'titles':
            inputfile = video.VideoFile(inputfile).set_tracks_title(**vals)
