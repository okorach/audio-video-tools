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
specs = videotools.videofile.get_file_specs(args.inputfile)
file_type = specs['format']['format_name']
myspecs = dict()
myspecs['file_name'] = specs['format']['filename']
myspecs['file_size'] = specs['format']['size']
if file_type == 'image2':
    myspecs['type'] = 'image'
elif file_type == 'mp3':
    myspecs['type'] = 'audio'
    myspecs['format'] = specs['streams'][0]['codec_name']
elif re.search(r'mp4', file_type) is not None:
    myspecs['type'] = 'video'
    myspecs['format'] = 'mp4'

for stream in specs['streams']:
    try:
        if myspecs['type'] == 'image':
            myspecs['image_codec'] = stream['codec_name']
            myspecs['width'] = stream['width']
            myspecs['height'] = stream['height']
            myspecs['format'] = stream['codec_name']
        elif myspecs['type'] == 'video' and stream['codec_type'] == 'video':
            myspecs['type'] = 'video'
            myspecs['video_codec'] = stream['codec_name']
            myspecs['video_bit_rate'] = stream['bit_rate']
            myspecs['width'] = stream['width']
            myspecs['height'] = stream['height']
            myspecs['duration'] = stream['duration']
            myspecs['duration_hms'] = videotools.videofile.to_hms_str(stream['duration'])
            myspecs['aspect_ratio'] = stream['display_aspect_ratio']
            myspecs['frame_rate'] = stream['r_frame_rate']
        elif (myspecs['type'] == 'audio' or myspecs['type'] == 'video') and stream['codec_type'] == 'audio':
            myspecs['audio_codec'] = stream['codec_name']
            myspecs['sample_rate'] = stream['sample_rate']
            myspecs['duration'] = stream['duration']
            myspecs['duration_hms'] = videotools.videofile.to_hms_str(stream['duration'])
            myspecs['audio_bit_rate'] = stream['bit_rate']
    except KeyError as e:
        print("Stream %s has no key %s" % (str(stream), e.args[0]))
nb_streams = specs['format']['nb_streams']

if (args.format is "txt" ):
    for param in myspecs:
        print("%-20s : %s" % (param, str(myspecs[param])))
else:
    # CSV format
    print("# ")
    for param in myspecs:
        print("%s; " % param, end='')
    print('')
    for param in myspecs:
        print("%s; " % str(myspecs[param]), end='')
    print('')