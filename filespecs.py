#!/usr/local/bin/python3

import sys
import os
import re
import argparse
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.audiofile as audio
import mediatools.mediafile as media
import mediatools.imagefile as img

parser = argparse.ArgumentParser(description='Audio/Video/Image file specs extractor')
parser.add_argument('-i', '--inputfile', required=True, help='Input file or directory to probe')
parser.add_argument('-f', '--format', required=False, default='txt', help='Output file format (txt or csv)')
parser.add_argument('-g', '--debug', required=False, default=0, help='Debug level')
args = parser.parse_args()
util.set_debug_level(int(args.debug))
options = util.cleanup_options(vars(args))

if os.path.isdir(args.inputfile):
    filelist = util.filelist(args.inputfile)
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
    if not util.is_media_file(file):
        continue
    try:
        if util.is_video_file(file):
            file_object = video.VideoFile(file)
        elif util.is_audio_file(file):
            file_object = audio.AudioFile(file)
        elif util.is_image_file(file):
            file_object = img.ImageFile(file)
        else:
            file_object = media.MediaFile(file)
        specs = file_object.get_properties()
        for prop in PROPS:
            if args.format != "csv":
                try:
                    if prop in UNITS.keys():
                        divider = UNITS[prop][0]
                        unit = UNITS[prop][1]
                        if unit is 'hms':
                            print("%-20s : %s" % (prop, util.to_hms_str(specs[prop])))
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
                        print("%s;" % util.to_hms_str(specs[prop]))
                except KeyError:
                    print("%s;" % '', end='')
        print('')
    except media.FileTypeError as e:
        print ('ERROR: File %s type error' % file)
