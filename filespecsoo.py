#!/usr/local/bin/python3

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

PROPS = ['filename', 'filesize', 'type', 'format', 'width', 'height', 'duration', \
    'video_codec', 'video_bitrate', 'aspect_ratio', 'pixel_aspect_ratio', 'video_fps', \
    'audio_codec', 'audio_bitrate', 'audio_sample_rate',  \
    'author', 'title', 'album', 'year', 'track', 'genre']

UNITS = { 'filesize' : [1048576, 'MB'], 'duration':[1,'hms'], 'video_bitrate':[1024, 'kbits/s'], \
          'audio_bitrate':[1024, 'kbits/s'], 'audio_sample_rate':[1000, 'k'], }

if args.format == 'csv':
    print("# ")
    for prop in PROPS:
        print("%s;" % prop, end='')
    print('')

for file in filelist:
    if not mediatools.utilities.is_media_file(file):
        continue
    try:
        if mediatools.utilities.is_video_file(file):
            file_object = mediatools.videofile.VideoFile(file)
        elif mediatools.utilities.is_audio_file(file):
            file_object = mediatools.videofile.AudioFile(file)
        elif mediatools.utilities.is_image_file(file):
            file_object = mediatools.videofile.MediaFile(file)
        else:
            file_object = mediatools.videofile.MediaFile(file)
        specs = file_object.get_properties()
        for prop in PROPS:
            if args.format != "csv":
                try:
                    if prop in UNITS.keys():
                        divider = UNITS[prop][0]
                        unit = UNITS[prop][1]
                        if unit is 'hms':
                            print("%-20s : %s" % (prop, mediatools.videofile.to_hms_str(specs[prop])))
                        else:
                            print("%-20s : %.1f %s" % (prop, (int(specs[prop])/divider), unit))
                    else:
                        print("%-20s : %s" % (prop, str(specs[prop]) if specs[prop] is not None else ''))
                except KeyError:
                    print("%-20s : %s" % (prop, ""))
            else:
                # CSV format
                try:
                    print("%s;" % (str(specs[prop]) if specs[prop] is not None else ''), end='')
                    if prop is 'duration':
                        print("%s;" % mediatools.videofile.to_hms_str(specs[prop]))
                except KeyError:
                    print("%s;" % '', end='')
        print('')
    except mediatools.videofile.FileTypeError as e:
        print ('ERROR: File %s type error' % file)