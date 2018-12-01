#!python3

import videotools.videofile
import sys
import os
import re
import argparse

def parse_args():
    parser = argparse.ArgumentParser(
            description='Get Audio/Video/Image file specifications')
    parser.add_argument('-i', '--inputfile', required=True,
                           help='Input file'
                        )
    parser.add_argument('-f', '--format', required=False,
                           help='Format of output specs'
                        )
    args = parser.parse_args()

    return args

args = parse_args()
if os.path.isdir(args.inputfile):
    filelist = videotools.videofile.filelist(args.inputfile)
else:
    filelist = [ args.inputfile ]

is_first = True

props = ['filename', 'filesize', 'type', 'format', 'width', 'height', 'video_codec', 'audio_codec', \
    'audio_bitrate', 'video_bitrate', 'duration', 'duration_hms', 'sample_rate', 'fps', 'aspect_ratio', \
    'author', 'title', 'album', 'year', 'track', 'genre']

if args.format is not 'txt':
    print("# ")
    for prop in props:
        print("%s;" % prop, end='')
    print('')

for file in filelist:
    if not videotools.videofile.is_media_file(file):
        continue
    try:
        myspecs = videotools.videofile.get_file_specs(file)
        for prop in props:
            if args.format is "txt":
                print("%-20s : %s" % (prop, str(myspecs[prop])))
            else:
                # CSV format
                try:
                    print("%s;" % str(myspecs[prop]), end='')
                except KeyError:
                    print("%s;" % '', end='')
        print('')
    except videotools.videofile.FileTypeError as e:
        print ('ERROR: File %s type error' % file)