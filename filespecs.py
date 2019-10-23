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
parser.add_argument('-t', '--types', required=False, default='', help='Types of files to include [audio,video,image]')
parser.add_argument('-g', '--debug', required=False, default=0, help='Debug level')
parser.add_argument('--dry_run', required=False, default=0, help='Dry run mode')
args = parser.parse_args()
options = vars(args)
util.check_environment(options)
util.cleanup_options(options)

filelist = []
if os.path.isdir(args.inputfile):
    if args.types == '':
        types = ['video', 'audio', 'image']
    else:
        types = re.split(',', args.types.lower())
    if 'video' in types:
        filelist.extend(util.video_filelist(args.inputfile))
    if 'audio' in types:
        filelist.extend(util.audio_filelist(args.inputfile))
    if 'image' in types:
        filelist.extend(util.image_filelist(args.inputfile))
else:
    filelist = [ args.inputfile ]

is_first = True

VIDEO_PROPS = ['filename', 'filesize', 'type', 'format', 'width', 'height', 'duration', \
    'video_codec', 'video_bitrate', 'aspect_ratio', 'pixel_aspect_ratio', 'video_fps', \
    'audio_codec', 'audio_bitrate', 'audio_language', 'audio_sample_rate',  'author']

AUDIO_PROPS = ['filename', 'filesize', 'type', 'format', 'duration', \
    'audio_codec', 'audio_bitrate', 'audio_sample_rate',  \
    'author', 'title', 'album', 'year', 'track', 'genre']

IMAGE_PROPS = ['filename', 'filesize', 'type', 'format', 'width', 'height', 'pixels', 'author', 'title']

UNITS = { 'filesize' : [1048576, 'MB'], 'duration':[1,'hms'], 'video_bitrate':[1024, 'kbits/s'], \
          'audio_bitrate':[1024, 'kbits/s'], 'audio_sample_rate':[1000, 'k'], 'pixels':[1000000, 'Mpix'] }

all_props = list(set(VIDEO_PROPS + AUDIO_PROPS + IMAGE_PROPS))

if args.format == 'csv':
    print("# ")
    for prop in all_props:
        print("%s;" % prop, end='')
        if prop == 'duration':
            print("%s;" % "Duration HH:MM:SS", end='')
    print('')

props = all_props
nb_files = len(filelist)
for file in filelist:
    try:
        if not util.is_media_file(file):
            raise media.FileTypeError("File %s is not a supported file format" % file)
        if util.is_video_file(file):
            file_object = video.VideoFile(file)
            if nb_files == 1:
                props = VIDEO_PROPS
        elif util.is_audio_file(file):
            file_object = audio.AudioFile(file)
            if nb_files == 1:
                props = AUDIO_PROPS
        elif util.is_image_file(file):
            file_object = img.ImageFile(file)
            if nb_files == 1:
                props = IMAGE_PROPS

        specs = file_object.get_properties()
        util.logger.debug("Specs = %s", util.json_fmt(specs))
        for prop in props:
            if args.format != "csv":
                try:
                    if prop in UNITS:
                        divider = UNITS[prop][0]
                        unit = UNITS[prop][1]
                        if unit == 'hms':
                            print("%-20s : %s" % (prop, util.to_hms_str(specs[prop])))
                        else:
                            print("%-20s : %.1f %s" % (prop, (int(specs[prop])/divider), unit))
                    else:
                        print("%-20s : %s" % (prop, str(specs[prop]) if specs[prop] is not None else ''))
                except KeyError:
                    print("%-20s : %s" % (prop, ""))
                except TypeError:
                    print("%-20s : %s" % (prop, "Wrong type"))
            else:
                # CSV format
                try:
                    print("%s;" % (str(specs[prop]) if specs[prop] is not None else ''), end='')
                    if prop == 'duration':
                        print("%s;" % util.to_hms_str(specs[prop]), end='')
                except KeyError:
                    print("%s;" % '', end='')
        print("")
    except media.FileTypeError as e:
        print ('ERROR: File %s type error' % file)
