#!python3

import mediatools.videofile
import sys
import os
import re
import argparse

parser = mediatools.videofile.parse_common_args('Audio/Video/Image file specs extractor')
args = parser.parse_args()
if args.debug:
    mediatools.utilities.set_debug_level(int(args.debug))
options = mediatools.videofile.cleanup_options(vars(args))

if os.path.isdir(args.inputfile):
    filelist = mediatools.utilities.filelist(args.inputfile)
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
    if not mediatools.utilities.is_media_file(file):
        continue
    try:
        myspecs = mediatools.videofile.get_file_specs(file)
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
    except mediatools.videofile.FileTypeError as e:
        print ('ERROR: File %s type error' % file)