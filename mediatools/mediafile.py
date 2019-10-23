#!/usr/local/bin/python3

import sys
import platform
import re
import os
import json
import shutil
import jprops
import ffmpeg
import mediatools.utilities as util

class FileTypeError(Exception):
    '''Error when passing a non media file'''
    pass
class MediaFile:
    '''Media file abstraction'''
    def __init__(self, filename):
        if not util.is_media_file(filename):
            raise FileTypeError('File %s is neither video, audio nor image file' % filename)
        self.type = util.get_file_type(filename)
        self.filename = filename
        self.specs = None
        self.author = None
        self.year =  None
        self.copyright = None
        self.format = None
        self.format_long = None
        self.nb_streams = None
        self.size = None
        self.bitrate = None
        self.duration = None

    def get_filename(self):
        '''Returns file name'''
        return self.filename

    def get_author(self):
        '''Returns file author'''
        return self.author

    def get_filetype(self):
        '''Returns filetype'''
        return self.type

    def get_year(self):
        '''Returns file year'''
        return self.year

    def get_copyright(self):
        '''Returns file copyright'''
        return self.copyright

    def probe(self):
        '''Returns media file general specs'''
        if self.specs is None:
            self.specs = self.probe2()
            json.dumps(self.specs, sort_keys=True, indent=3, separators=(',', ': '))
        if self.specs is not None:
            self.get_format_specs()
        return self.specs

    def get_format_specs(self):
        '''Reads file format specs'''
        self.format = self.specs['format']['format_name']
        self.format_long = self.specs['format']['format_long_name']
        self.nb_streams = self.specs['format']['nb_streams']
        self.size = self.specs['format']['size']
        try:
            self.bitrate = self.specs['format']['bit_rate']
        except KeyError:
            pass
        try:
            self.duration = self.specs['format']['duration']
        except KeyError:
            pass

    def get_file_properties(self):
        '''Returns file properties as dict'''
        return {'filename':self.filename, 'type':self.type, 'format':self.format, \
        'nb_streams':self.nb_streams, 'filesize':self.size, 'duration': self.duration, \
        'bitrate':self.bitrate}

    def probe2(self):
        ''' Returns file probe (media specs) '''
        try:
            util.logger.info('Probing %s', self.filename)
            return ffmpeg.probe(self.filename, cmd=util.get_ffprobe())
        except AttributeError:
            print (dir(ffmpeg))
        except ffmpeg.Error:
            return None

    def get_stream_by_codec(self, field, value):
        util.logger.debug('Searching stream for codec %s = %s', field, value)
        for stream in self.specs['streams']:
            util.logger.debug('Found codec %s', stream[field])
            if stream[field] == value:
                return stream
        return None

def build_target_file(source_file, profile):
    extension = util.get_profile_extension(profile)
    if extension is None:
        extension = util.get_file_extension(source_file)
    return util.add_postfix(source_file, profile, extension)

def cmdline_options(**kwargs):
    # Returns ffmpeg cmd line options converted from clear options to ffmpeg format
    util.logger.debug('Building cmd line options from %s', str(kwargs))
    if kwargs is None:
        return {}
    params = {}
    for key in util.OPTIONS_MAPPING:
        util.logger.debug("Checking option %s", key)
        try:
            if kwargs[key] is not None:
                util.logger.debug("Found in cmd line with value %s", kwargs[key])
                params[util.OPTIONS_MAPPING[key]] = kwargs[key]
        except KeyError:
            pass
    return params

def get_crop_filter_options(width, height, top, left):
    # ffmpeg -i in.mp4 -filter:v "crop=out_w:out_h:x:y" out.mp4
    return "-filter:v crop=%d:%d:%d:%d" % (width, height, top, left)

def get_deshake_filter_options(width, height):
    # ffmpeg -i <in> -f mp4 -vf deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=16 -b:v 2048k <out>
    return "-vf deshake=x=-1:y=-1:w=-1:h=-1:rx=%d:ry=%d" % (width, height)

def probe_file(file):
    ''' Returns file probe (media specs) '''
    if util.is_media_file(file):
        try:
            return ffmpeg.probe(file, cmd=util.get_ffprobe())
        except AttributeError:
            print(dir(ffmpeg))
    else:
        raise FileTypeError('File %s is neither video, audio nor image file' % file)

def compute_fps(rate):
    ''' Simplifies the FPS calculation '''
    util.logger.debug('Calling compute_fps(%s)', rate)
    if re.match(r"^\d+\/\d+$", rate):
        a, b = re.split(r'/', rate)
        return str(round(int(a)/int(b), 1))
    return rate

def reduce_aspect_ratio(aspect_ratio, height=None):
    ''' Reduces the Aspect ratio calculation in prime factors '''
    if height is None:
        ws, hs = re.split("[:/x]", aspect_ratio)
        w = int(ws)
        h = int(hs)
    else:
        w = aspect_ratio
        h = height
    for n in [2, 3, 5, 7, 11, 13, 17]:
        while w % n == 0 and h % n == 0:
            w = w // n
            h = h // n
    return "%d:%d" % (w, h)

def get_audio_specs(stream):
    specs = {}
    specs['audio_codec'] = stream['codec_name']
    specs['audio_sample_rate'] = stream['sample_rate']
    try:
        specs['duration'] = stream['duration']
        specs['duration_hms'] = to_hms_str(stream['duration'])
    except KeyError:
        pass
    specs['audio_bitrate'] = stream['bit_rate']
    return specs

def get_video_bitrate(stream):
    bitrate = None
    bitrate = stream.get('bit_rate', None)
    if bitrate is None:
        bitrate = stream.get('duration_ts', None)
    return bitrate

def get_video_specs(stream):
    util.logger.debug("Getting stream data %s", json.dumps(stream, sort_keys=True, indent=3, separators=(',', ': ')))
    specs = {}
    specs['type'] = 'video'
    specs['video_codec'] = stream['codec_name']
    specs['video_bitrate'] = get_video_bitrate(stream)
    specs['width'] = stream['width']
    specs['height'] = stream['height']
    specs['duration'] = stream['duration']
    specs['duration_hms'] = to_hms_str(stream['duration'])
    raw_fps = stream['avg_frame_rate'] if 'avg_frame_rate' in stream.keys() else stream['r_frame_rate']
    specs['video_fps'] = compute_fps(raw_fps)
    specs['video_aspect_ratio'] = stream.get('display_aspect_ratio', None)
    if specs['video_aspect_ratio'] is None:
        specs['video_aspect_ratio'] = reduce_aspect_ratio(specs['width'], specs['height'])
    return specs

def get_image_specs(stream):
    specs = {}
    specs['image_codec'] = stream['codec_name']
    specs['width'] = stream['width']
    specs['height'] = stream['height']
    specs['format'] = stream['codec_name']
    return specs

def get_file_specs(file):
    probe_data = probe_file(file)
    util.logger.debug(json.dumps(probe_data, sort_keys=True, indent=3, separators=(',', ': ')))
    specs = {}
    specs['filename'] = probe_data['format']['filename']
    specs['filesize'] = probe_data['format']['size']
    #if file_type == 'image2':
    specs['type'] = util.get_file_type(file)
    if util.is_audio_file(file):
        specs['format'] = probe_data['streams'][0]['codec_name']
    #elif re.search(r'mp4', file_type) is not None:
    elif util.is_video_file(file):
        specs['format'] = util.get_file_extension(file)

    util.logger.debug("File type %s", specs['type'])
    for stream in probe_data['streams']:
        try:
            if specs['type'] == 'image':
                specs.update(get_image_specs(stream))
            elif specs['type'] == 'video' and stream['codec_type'] == 'video':
                specs.update(get_video_specs(stream))
            elif (specs['type'] == 'audio' or specs['type'] == 'video') and stream['codec_type'] == 'audio':
                specs.update(get_audio_specs(stream))
        except KeyError as e:
            util.logger.error("Stream %s has no key %s\n%s", str(stream), e.args[0], str(specs))
    return specs

def to_hms(seconds):
    s = float(seconds)
    hours = int(s)//3600
    minutes = int(s)//60 - hours*60
    secs = s - hours*3600 - minutes*60
    return (hours, minutes, secs)

def to_hms_str(seconds):
    hours, minutes, secs = to_hms(seconds)
    return "%d:%02d:%06.3f" % (hours, minutes, secs)

def get_mp3_tags(file):
    from mp3_tagger import MP3File
    if util.get_file_extension(file).lower() != 'mp3':
        raise FileTypeError('File %s is not an mp3 file')
    # Create MP3File instance.
    mp3 = MP3File(file)
    return {'artist' : mp3.artist, 'author' : mp3.artist, 'song' : mp3.song, 'title' : mp3.song, \
        'album' : mp3.album, 'year' : mp3.year, 'track' : mp3.track, 'genre' : mp3.genre, 'comment' : mp3.comment}

def concat(target_file, file_list):
#    ffmpeg -i opening.mkv -i episode.mkv -i ending.mkv \
#  -filter_complex "[0:v] [0:a] [1:v] [1:a] [2:v] [2:a] concat=n=3:v=1:a=1 [v] [a]" \
#  -map "[v]" -map "[a]" output.mkv
    util.logger.info("Concatenating %s", str(file_list))
    cmd = util.build_ffmpeg_file_list(file_list)
    cmd = cmd + '-filter_complex "'
    for i in range(len(file_list)):
        cmd = cmd + ('[%d:v] [%d:a] ' % (i, i))
    cmd = cmd + 'concat=n=%d:v=1:a=1 [v] [a]" -map "[v]" -map "[a]" %s' % (len(file_list), target_file)
    util.run_ffmpeg(cmd)

def build_ffmpeg_options(options):
    cmd = ''
    for option in options.keys():
        if options[option] is not None:
            cmd = cmd + " -%s %s" % (option, options[option])
    return cmd

def build_video_filters_options(filters):
    cmd = ''
    for f in filters:
        cmd = cmd + '-vf "%s" ' % f
    return cmd
