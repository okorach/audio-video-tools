#!/usr/local/bin/python3

import videotools.videofile
import sys
import os
import re
import argparse

parser = videotools.videofile.parse_common_args('Audio/Video/Image file specs extractor')
args = parser.parse_args()
if args.debug:
    videotools.filetools.set_debug_level(int(args.debug))
options = videotools.videofile.cleanup_options(vars(args))

if os.path.isdir(args.inputfile):
    filelist = videotools.filetools.filelist(args.inputfile)
else:
    filelist = [ args.inputfile ]

is_first = True

props = ['filename', 'filesize', 'type', 'format', 'width', 'height', 'duration', \
    'video_codec', 'video_bitrate', 'aspect_ratio', 'pixel_aspect_ratio', 'video_fps', \
    'audio_codec', 'audio_bitrate', 'audio_sample_rate',  \
    'author', 'title', 'album', 'year', 'track', 'genre']

if args.format != 'txt':
    print("# ")
    for prop in props:
        print("%s;" % prop, end='')
    print('')

for file in filelist:
    if not videotools.filetools.is_media_file(file):
        continue
    try:
        if videotools.filetools.is_video_file(file):
            file_object = videotools.videofile.VideoFile(file)
        elif videotools.filetools.is_audio_file(file):
            file_object = videotools.videofile.AudioFile(file)
        elif videotools.filetools.is_image_file(file):
            file_object = videotools.videofile.MediaFile(file)
        else:
            file_object = videotools.videofile.MediaFile(file)
        specs = file_object.get_properties()
        for prop in props:
            if args.format == "txt":
                try:
                    if prop is 'duration':
                        print("%-20s : %s" % (prop, videotools.videofile.to_hms_str(specs[prop])))
                    elif prop is 'filesize':
                        print("%-20s : %.1f MB" % (prop, videotools.filetools.to_m(specs[prop])))
                    else:
                        print("%-20s : %s" % (prop, str(specs[prop]) if specs[prop] is not None else ''))
                except KeyError:
                    print("%-20s : %s" % (prop, ""))
            else:
                # CSV format
                try:
                    print("%s;" % (str(specs[prop]) if specs[prop] is not None else ''), end='')
                    if prop is 'duration':
                        print("%s;" % videotools.videofile.to_hms_str(specs[prop]))
                except KeyError:
                    print("%s;" % '', end='')
        print('')
    except videotools.videofile.FileTypeError as e:
        print ('ERROR: File %s type error' % file)