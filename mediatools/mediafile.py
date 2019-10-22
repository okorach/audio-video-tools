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

class Encoder:
    '''Encoder abstraction'''
    def __init__(self):
        self.format = None
        self.vcodec = None # 'libx264'
        self.acodec = None # 'libvo_aacenc'
        self.vbitrate = None # '2048k'
        self.abitrate = None # '128k'
        self.fps = None
        self.aspect = None
        self.size = None
        self.deinterlace = None
        self.achannels = None
        self.vfilters = {}
        self.other_options = {}

    def set_ffmpeg_properties(self, props):
        '''Set Encoder properties according to ffmpeg conventions'''
        params = util.get_cmdline_params(props)
        for param in params:
            if param == util.FFMPEG_FORMAT_OPTION:
                self.format = params[param]
            elif param == util.FFMPEG_VBITRATE_OPTION:
                self.vbitrate = params[param]
            elif param == util.FFMPEG_VCODEC_OPTION:
                self.vcodec = params[param]
            elif param == util.FFMPEG_ABITRATE_OPTION:
                self.abitrate = params[param]
            elif param == util.FFMPEG_ACODEC_OPTION:
                self.acodec = params[param]
            elif param == util.FFMPEG_DEINTERLACE_OPTION:
                self.deinterlace = ''
            elif param == util.FFMPEG_FPS_OPTION:
                self.fps = params[param]
            elif param == util.FFMPEG_SIZE_OPTION:
                self.size = params[param]
            elif param == util.FFMPEG_ASPECT_OPTION:
                self.aspect = params[param]
            elif param == util.FFMPEG_ACHANNEL_OPTION:
                self.achannels = params[param]
            elif param == util.FFMPEG_VFILTER_OPTION:
                self.vfilters.update({util.FFMPEG_VFILTER_OPTION:params[param]})

    def set_vcodec(self, vcodec):
        '''Set vcodec'''
        self.vcodec = vcodec

    def set_size(self, size):
        '''Set video size'''
        self.size = size

    def set_acodec(self, acodec):
        '''Set audio codec'''
        self.acodec = acodec

    def set_vbitrate(self, bitrate):
        '''Set video bitrate'''
        self.vbitrate = bitrate

    def set_abitrate(self, bitrate):
        '''Set audio bitrate'''
        self.abitrate = bitrate

    def set_deinterlace(self):
        '''Apply deinterlace'''
        self.deinterlace = ''

    def set_format(self, fmt):
        '''Set video file format'''
        self.format = fmt

    def build_ffmpeg_options(self):
        '''Builds string corresponding to ffmpeg conventions'''
        options = vars(self)
        cmd = ''
        for option in options.keys():
            if options[option] is not None:
                cmd = cmd + " -%s %s" % (util.OPTIONS_MAPPING[option], options[option])
        return cmd

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
        self.probe()

    def get_filename(self):
        '''Returns file name'''
        return self.filename

    def get_author(self):
        '''Returns file author'''
        if self.author is None:
            self.probe()
        return self.author

    def get_filetype(self):
        '''Returns filetype'''
        return self.type

    def get_year(self):
        '''Returns file year'''
        if self.year is None:
            self.probe()
        return self.year

    def get_copyright(self):
        '''Returns file copyright'''
        if self.copyright is None:
            self.probe()
        return self.copyright

    def probe(self):
        '''Returns media file general specs'''
        if self.specs is not None:
            return self.specs
        try:
            util.logger.info('Probing %s', self.filename)
            self.specs = ffmpeg.probe(self.filename, cmd=util.get_ffprobe())
        except AttributeError:
            print (dir(ffmpeg))
        except ffmpeg.Error:
            return None
        util.logger.debug(util.json_fmt(self.specs))
        return self.specs

    def get_format_specs(self):
        '''Reads file format specs'''
        self.format = self.specs['format']['format_name']
        self.format_long = self.specs['format']['format_long_name']
        self.nb_streams = int(self.specs['format']['nb_streams'])
        self.size = int(self.specs['format']['size'])
        try:
            self.bitrate = int(self.specs['format']['bit_rate'])
        except KeyError:
            pass
        try:
            self.duration = float(self.specs['format']['duration'])
        except KeyError:
            pass

    def get_file_properties(self):
        '''Returns file properties as dict'''
        return {'filename':self.filename, 'type':self.type, 'format':self.format, \
        'nb_streams':self.nb_streams, 'filesize':self.size, 'duration': self.duration, \
        'bitrate':self.bitrate}

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
