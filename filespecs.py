#!python3

import sys
import os
import re
import argparse
import mediatools.videofile as video
import mediatools.mediafile as media
import mediatools.utilities as util

parser = util.parse_common_args('Audio/Video/Image file specs extractor')
args = parser.parse_args()
if args.util.debug:
    util.set_debug_level(int(args.util.debug))
options = util.cleanup_options(vars(args))

if os.path.isdir(args.inputfile):
    filelist = util.filelist(args.inputfile)
else:
    filelist = [ args.inputfile ]

is_first = True

props = ['filename', 'filesize', 'type', 'format', 'width', 'height', 'duration', 'duration_hms', \
    'video_codec', 'video_bitrate', 'video_aspect_ratio', 'video_fps', \
    'audio_codec', 'audio_bitrate', 'audio_sample_rate',  \
    'author', 'title', 'album', 'year', 'track', 'genre']

if args.format != 'txt':
    print("# ")
    for prop in props:
        print("%s;" % prop, end='')
    print('')

for file in filelist:
    if not util.is_media_file(file):
        continue
    try:
        myspecs = video.get_file_specs(file)
        for prop in props:
            if args.format == "txt":
                try:
                    print("%-20s : %s" % (prop, str(myspecs[prop])))
                except KeyError:
                    print("%-20s : %s" % (prop, ""))
            else:
                # CSV format
                try:
                    print("%s;" % str(myspecs[prop]), end='')
                except KeyError:
                    print("%s;" % '', end='')
        print('')
    except media.FileTypeError as e:
        print ('ERROR: File %s type error' % file)