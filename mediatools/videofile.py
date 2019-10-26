#!/usr/local/bin/python3

'''Video file tools'''

from __future__ import print_function
import sys
import re
import os
import json
import shutil
import ffmpeg
import jprops
import mediatools.utilities as util
import mediatools.mediafile as media

class VideoFile(media.MediaFile):
    '''Video file abstraction'''
    def __init__(self, filename):
        if not util.is_video_file(filename):
            raise media.FileTypeError('File {0} is not a video file'.format(filename))

        self.aspect = None
        self.video_codec = None
        self.video_bitrate = None
        self.width = None
        self.height = None
        self.pixels = None
        self.duration = None
        self.video_fps = None
        self.pixel_aspect = None
        self.audio_bitrate = None
        self.audio_codec = None
        self.audio_language = None
        self.audio_sample_rate = None
        self.stream = None
        super(VideoFile, self).__init__(filename)
        self.get_specs()

    def get_specs(self):
        '''Returns video file complete specs as dict'''
        if self.specs is None:
            self.probe()
        self.decode_specs()

    def decode_specs(self):
        self.get_file_specs()
        self.get_video_specs()
        self.get_audio_specs()

    def get_video_specs(self):
        '''Returns video file video specs as dict'''
        stream = self.__get_first_video_stream__()
        _, _ = self.get_dimensions(stream)
        _ = self.get_fps(stream)
        _ = self.get_video_codec(stream)
        _ = self.get_pixel_aspect_ratio(stream)
        try:
            self.video_bitrate = get_video_bitrate(stream)
            if self.video_bitrate is None:
                self.video_bitrate = self.specs['format']['bit_rate']
            self.duration = stream['duration']
        except KeyError as e:
            util.logger.error("Stream %s has no key %s\n", str(stream), e.args[0])

        return self.specs

    def get_audio_specs(self):
        '''Returns video file audio specs as dict'''
        for stream in self.specs['streams']:
            if stream['codec_type'] != 'audio':
                continue
            self.audio_codec = self.__get_audio_stream_attribute__('codec_name')
            self.audio_bitrate = self.__get_audio_stream_attribute__('bit_rate')
            self.audio_sample_rate = self.__get_audio_stream_attribute__('sample_rate')
            if 'tags' in stream and 'language' in stream['tags']:
                self.audio_language = stream['tags']['language']
                if self.audio_language in util.LANGUAGE_MAPPING:
                    self.audio_language = util.LANGUAGE_MAPPING[self.audio_language]
            break
        return self.specs

    def get_aspect_ratio(self):
        '''Returns video file aspect ratio'''
        if self.aspect is None:
            self.get_specs()
        return self.aspect

    def get_pixel_aspect_ratio(self, stream = None):
        '''Returns video file pixel aspect ratio'''
        if self.pixel_aspect is None:
            ar = stream.get('display_aspect_ratio', None)
            if ar is None:
                ar = "%d:%d" % (self.width, self.height)
            self.aspect = media.reduce_aspect_ratio(ar)
            par = stream.get('sample_aspect_ratio', None)
            if par is None:
                par = media.reduce_aspect_ratio("%d:%d" % (self.width, self.height))
            self.pixel_aspect = media.reduce_aspect_ratio(par)
        return self.pixel_aspect

    def get_video_codec(self, stream):
        '''Returns video file video codec'''
        util.logger.debug('Getting video codec')
        if self.video_codec is not None:
            return self.video_codec
        if stream is None:
            stream = self.__get_first_video_stream__()
        try:
            self.video_codec = stream['codec_name']
        except KeyError as e:
            util.logger.error("Stream %s has no key %s\n", util.json_fmt(stream), e.args[0])
        return self.video_codec


    def get_video_bitrate(self):
        '''Returns video file video bitrate'''
        if self.video_bitrate is None:
            try:
                self.video_bitrate = self.specs['format']['bit_rate']
            except KeyError as e:
                util.logger.error("Format %s has no key %s\n", util.json_fmt(self.specs['format']), e.args[0])

    def get_video_duration(self, stream = None):
        if self.duration is None:
            self.duration = self.__get_video_stream_attribute__('duration')
        return self.duration

    def get_audio_codec(self):
        '''Returns video file audio codec'''
        if self.audio_codec is None:
            self.get_specs()
        return self.audio_codec

    def get_audio_bitrate(self):
        '''Returns video file audio bitrate'''
        if self.audio_bitrate is None:
            self.get_specs()
        return self.audio_bitrate

    def get_duration(self):
        '''Returns video file duration'''
        if self.duration is None:
            self.get_specs()
        return self.duration

    def get_height(self):
        '''Returns video file height'''
        if self.height is None:
            self.get_specs()
        return self.height

    def get_width(self):
        '''Returns video file width'''
        if self.width is None:
            self.get_specs()
        return self.width


    def get_fps(self, stream = None):
        if self.video_fps is None:
            if stream is None:
                stream = self.__get_first_video_stream__()
                util.logger.debug('Video stream is %s', util.json_fmt(stream))
            for tag in [ 'avg_frame_rate', 'r_frame_rate']:
                if tag in stream:
                    self.video_fps = media.compute_fps(stream[tag])
                    break
        return self.video_fps

    def get_dimensions(self, stream = None):
        util.logger.debug('Getting video dimensions')
        if self.width is None or self.height is None:
            if stream is None:
                stream = self.__get_first_video_stream__()
            if self.width is None:
                self.width = util.get_first_value(stream, [ 'width', 'codec_width', 'coded_width'])
            if self.height is None:
                self.height = util.get_first_value(stream, [ 'height', 'codec_height', 'coded_height'])
            if self.width is not None and self.height is not None:
                self.pixels = self.width * self.height
        util.logger.debug("Returning [%s, %s]", str(self.width), str(self.height))
        return [self.width, self.height]

    def get_audio_properties(self):
        if self.audio_codec is None:
            self.get_specs()
        return {'audio_bitrate': self.audio_bitrate, 'audio_codec': self.audio_codec, \
        'audio_language': self.audio_language, 'audio_sample_rate': self.audio_sample_rate }

    def get_video_properties(self):
        if self.video_codec is None:
            self.get_specs()
        return {'file_size':self.size, 'file_format': self.format, 'video_bitrate': self.video_bitrate, \
        'video_codec': self.video_codec, 'video_fps':self.video_fps, \
        'width':self.width, 'height': self.height, 'aspect_ratio': self.aspect, \
        'pixel_aspect_ratio': self.pixel_aspect,'author': self.author, \
        'copyright': self.copyright, 'year':self.year }

    def get_properties(self):
        all_props = self.get_file_properties()
        all_props.update(self.get_audio_properties())
        all_props.update(self.get_video_properties())
        return all_props

    def build_encoding_options(self, **kwargs):
        parms = self.get_ffmpeg_params()
        util.logger.info("File settings = %s", str(parms))
        if 'profile' in kwargs.keys():
            parms.update(util.get_cmdline_params(kwargs['profile']))
        util.logger.info("Profile settings = %s", str(parms))
        clean_options = util.cleanup_options(**kwargs)
        parms.update(media.cmdline_options(**clean_options))
        util.logger.info("Cmd line settings = %s", str(parms))

    def get_ffmpeg_params(self):
        mapping = { 'audio_bitrate':'b:a', 'audio_codec':'acodec', 'video_bitrate':'b:v', 'video_codec':'vcodec'}
        props = self.get_properties()
        ffmpeg_parms = {}
        for key in mapping:
            if props[key] is not None and props[key] != '':
                ffmpeg_parms[mapping[key]] = props[key]
        return ffmpeg_parms

    def scale(self, scale):
        self.stream = ffmpeg.filter_(self.stream, 'scale', size=scale)

    def crop(self, width, height, top, left, out_file, **kwargs):
        ''' Applies crop video filter for width x height pixels '''
        parms = self.get_ffmpeg_params()
        clean_options = util.cleanup_options(kwargs)
        parms.update(media.cmdline_options(**clean_options))
        util.logger.info("Cmd line settings = %s", str(parms))
        out_file = util.automatic_output_file_name(out_file, self.filename, \
            "crop_{0}x{1}-{2}x{3}".format(width, height, top, left))
        aspect = __get_aspect_ratio__(width, height, **kwargs)

        cmd = '-i "%s" %s %s -aspect %s "%s"' % (self.filename, \
            media.build_ffmpeg_options(parms), media.get_crop_filter_options(width, height, top, left), \
            aspect, out_file)
        util.run_ffmpeg(cmd)
        return out_file

    def cut(self, start, stop, out_file = None, **kwargs):
        if out_file is None:
            out_file = util.automatic_output_file_name(out_file, self.filename, "cut_%s-to-%s" % (start, stop))
        util.logger.debug("Cutting %s from %s to %s into %s", self.filename, start, stop, out_file)
        parms = self.get_ffmpeg_params()
        kwargs['start'] = start
        kwargs['stop'] = stop
        parms.update(media.cmdline_options(**kwargs))

        video_filters = []
        if 'fade' in kwargs and kwargs['fade'] is not None:
            fade_d = int(kwargs['fade'])
            fmt = "fade=type={0}:duration={1}:start_time={2}"
            fader = fmt.format('in', fade_d, start) + "," + fmt.format('out', fade_d, stop - fade_d)
            video_filters.append(fader)

        util.run_ffmpeg('-i "%s" %s %s "%s"' % (self.filename, media.build_ffmpeg_options(parms),
                                                media.build_video_filters_options(video_filters), out_file))

        return out_file

    def deshake(self, width, height, out_file, **kwargs):
        ''' Applies deshake video filter for width x height pixels '''
        parms = self.get_ffmpeg_params()
        clean_options = util.cleanup_options(kwargs)
        parms.update({'deinterlace':'', 'aspect':self.get_aspect_ratio()})
        parms.update(media.cmdline_options(**clean_options))

        if out_file is None or 'nocrop' in kwargs:
            output_file = util.add_postfix(self.filename, "deshake_%dx%d" % (width, height))
        else:
            output_file = out_file
        cmd = '-i "%s" %s %s "%s"' % (self.filename, \
            media.build_ffmpeg_options(parms), get_deshake_filter_options(width, height), output_file)
        util.run_ffmpeg(cmd)

        if 'nocrop' not in kwargs:
            return output_file

        new_w = self.get_width() - width
        new_h = self.get_height() - height
        if out_file is None:
            output_file2 = util.add_postfix(self.filename, "deshake_crop_%dx%d" % (new_w, new_h))
        else:
            output_file2 = out_file
        deshake_file_o = VideoFile(output_file)
        kwargs.update({'aspect': self.get_aspect_ratio()})
        deshake_file_o.crop(new_w, new_h, width//2, height//2, output_file2, **kwargs)
        os.remove(output_file)
        return output_file2

    def set_author(self, author):
        self.author = author

    def get_author(self):
        return self.author

    def set_copyright(self, copyr):
        self.copyright = copyr

    def get_copyright(self):
        return self.copyright

    def encode(self, target_file, profile, **kwargs):
        '''Encodes a file
        - target_file is the name of the output file. Optional
        - Profile is the encoding profile as per the VideoTools.properties config file
        - **kwargs accepts at large panel of other ptional options'''
        properties = util.get_media_properties()
        profile_options = properties[profile + '.cmdline']
        if target_file is None:
            target_file = build_target_file(self.filename, profile, properties)

        parms = {}
        video_filters = []
        parms = self.get_ffmpeg_params()
        util.logger.debug("File settings = %s", str(parms))

        parms.update(util.get_cmdline_params(profile_options))
        util.logger.debug("Profile settings = %s", str(parms))
        parms.update(media.cmdline_options(**kwargs))
        util.logger.debug("Cmd line settings = %s", str(parms))

        # Hack for channels selection
        mapping = __get_audio_channel_mapping__(**kwargs)

        video_filters.append(self.__get_fader_filter__(**kwargs))

        util.run_ffmpeg('-i "%s" %s %s %s "%s"' % (self.filename, media.build_ffmpeg_options(parms), \
                        media.build_video_filters_options(video_filters), mapping, target_file))
        util.logger.info("File %s encoded", target_file)

    #------------------ Private methods ------------------------------------------


    def __get_fader_filter__(self, **kwargs):
        if 'fade' in kwargs and kwargs['fade'] is not None:
            fade_d = int(kwargs['fade'])
            start = util.to_seconds(kwargs['start']) if 'start' in kwargs else 0
            stop = util.to_seconds(kwargs['stop']) if 'stop' in kwargs else float(self.get_duration())
            fmt = "fade=type={0}:duration={1}:start_time={2}"
            return fmt.format('in', fade_d, start) + "," + fmt.format('out', fade_d, stop-fade_d)
        return None

#---------------- Class methods ---------------------------------
def get_size_option(cmdline):
    m = re.search(r'-s\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_video_codec_option(cmdline):
    m = re.search(r'-vcodec\s+(\S+)', cmdline)
    if m:
        return m.group(1)
    m = re.search(r'-c:v\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_audio_codec_option(cmdline):
    m = re.search(r'-acodec\s+(\S+)', cmdline)
    if m:
        return m.group(1)
    m = re.search(r'-c:a\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_format_option(cmdline):
    m = re.search(r'-f\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_audio_bitrate_option(cmdline):
    m = re.search(r'-ab\s+(\S+)', cmdline)
    if m:
        return m.group(1)
    m = re.search(r'-b:a\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_video_bitrate_option(cmdline):
    m = re.search(r'-vb\s+(\S+)', cmdline)
    if m:
        return m.group(1)
    m = re.search(r'-b:v\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_aspect_ratio_option(cmdline):
    m = re.search(r'-aspect\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_frame_rate_option(cmdline):
    m = re.search(r'-r\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def build_target_file(source_file, profile, properties):
    extension = util.get_profile_extension(profile, properties)
    if extension is None:
        extension = util.get_file_extension(source_file)
    return util.add_postfix(source_file, profile, extension)

def get_crop_filter_options(width, height, top, left):
    # ffmpeg -i in.mp4 -filter:v "crop=out_w:out_h:x:y" out.mp4
    return "-filter:v crop={0}:{1}:{2}:{3}".format_map(width, height, top, left)

def get_deshake_filter_options(width, height):
    # ffmpeg -i <in> -f mp4 -vf deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=16 -b:v 2048k <out>
    return "-vf deshake=x=-1:y=-1:w=-1:h=-1:rx={0}:ry={1}".format(width, height)

def deshake(video_file, width, height, out_file = None, **kwargs):
    ''' Applies deshake video filter for width x height pixels '''
    return VideoFile(video_file).deshake(width, height, out_file, **kwargs)

def get_video_bitrate(stream):
    bitrate = None
    try:
        bitrate = stream['bit_rate']
    except KeyError:
        pass
    return bitrate

def get_mp3_tags(file):
    from mp3_tagger import MP3File
    if util.get_file_extension(file).lower() != 'mp3':
        raise media.FileTypeError('File %s is not an mp3 file')
    # Create MP3File instance.
    mp3 = MP3File(file)
    return { 'artist' : mp3.artist, 'author' : mp3.artist, 'song' : mp3.song, 'title' : mp3.song, \
        'album' : mp3.album, 'year' : mp3.year, 'track' : mp3.track, 'genre' : mp3.genre, 'comment' : mp3.comment }

def concat(target_file, file_list):
    '''Concatenates several video files - They must have same video+audio format and bitrate'''
    util.logger.info("%s = %s", target_file, ' + '.join(file_list))
    cmd = ''
    for file in file_list:
        cmd += (' -i "%s" ' % file)
    count = 0
    cmd += '-filter_complex "'
    for file in file_list:
        cmd += ("[%d:v][%d:a]" % (count, count))
        count += 1
    cmd += 'concat=n=%d:v=1:a=1[outv][outa]" -map "[outv]" -map "[outa]" "%s"' % (count, target_file)
    util.run_ffmpeg(cmd.strip())

def add_video_args(parser):
    """Parses options specific to video encoding scripts"""
    parser.add_argument('-p', '--profile', required=False, help='Profile to use for encoding')

    parser.add_argument('--vcodec', required=False, help='Video codec (h264, h265, mp4, mpeg2, xvid...)')
    parser.add_argument('--acodec', required=False, help='Audio codec (mp3, aac, ac3...)')

    parser.add_argument('--vbitrate', required=False, help='Video bitrate eg 1024k')
    parser.add_argument('--abitrate', required=False, help='Audio bitrate eg 128k')

    parser.add_argument('--fade', required=False, help='Fade in/out duration')

    parser.add_argument('-t', '--timeranges', required=False, help='Ranges of encoding <start>:<end>,<start>:<end>')
    parser.add_argument('--start', required=False, help='Start time')
    parser.add_argument('--stop', required=False, help='Stop time')

    parser.add_argument('-f', '--format', required=False, help='Output file format eg mp4')
    parser.add_argument('-r', '--fps', required=False, help='Video framerate of the output eg 25')


    parser.add_argument('--asampling', required=False, help='Audio sampling eg 44100')
    parser.add_argument('--achannels', required=False, help='Audio channel to pick')

    parser.add_argument('--vsize', required=False, help='Video size HxW')
    parser.add_argument('--vwidth', required=False, help='Video width')
    parser.add_argument('--vheight', required=False, help='Video height')

    return parser

def __get_aspect_ratio__(width, height, **kwargs):
    if 'aspect' not in kwargs or kwargs['aspect'] is None:
        aw, ah = re.split(":", media.reduce_aspect_ratio(width, height))
    else:
        aw, ah = re.split(":", kwargs['aspect'])
    return "{0}:{1}".format(aw, ah)

def __get_audio_channel_mapping__(**kwargs):
    # Hack for channels selection
    mapping = ''
    if 'achannels' in kwargs and kwargs['achannels'] is not None:
        mapping = "-map 0:v:0"
        for channel in kwargs['achannels'].split(','):
            mapping += " -map 0:a:{0}".format(channel)
    return mapping
