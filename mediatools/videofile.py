#!/usr/local/bin/python3

'''Video file tools'''

from __future__ import print_function
import sys
import re
import os
import random
import json
import shutil
import ffmpeg
import jprops
import mediatools.utilities as util
import mediatools.mediafile as media
import mediatools.imagefile as image
import mediatools.options as opt
import mediatools.filters as filters

FFMPEG_CLASSIC_FMT = '-i "{0}" {1} "{2}"'



class VideoFile(media.MediaFile):
    AV_PASSTHROUGH = '-{0} copy -{1} copy -map 0 '.format(opt.ff.VCODEC, opt.ff.ACODEC)
    DEFAULT_RESOLUTION = '3840x2160'

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
                self.video_bitrate = int(self.specs['format']['bit_rate'])
            self.duration = float(stream['duration'])
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
                self.video_bitrate = int(self.specs['format']['bit_rate'])
            except KeyError as e:
                util.logger.error("Format %s has no key %s\n", util.json_fmt(self.specs['format']), e.args[0])
        return self.video_bitrate

    def get_video_duration(self, stream = None):
        if self.duration is None:
            self.duration = float(self.__get_video_stream_attribute__('duration'))
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
                self.width = int(util.get_first_value(stream, [ 'width', 'codec_width', 'coded_width']))
            if self.height is None:
                self.height = int(util.get_first_value(stream, [ 'height', 'codec_height', 'coded_height']))
            if self.width is not None and self.height is not None:
                self.pixels = self.width * self.height
        util.logger.debug("Returning [%s, %s]", str(self.width), str(self.height))
        return [self.width, self.height]

    def get_audio_properties(self):
        if self.audio_codec is None:
            self.get_specs()
        return {opt.media.ABITRATE: self.audio_bitrate, opt.media.ACODEC: self.audio_codec, \
        'audio_language': self.audio_language, 'audio_sample_rate': self.audio_sample_rate }

    def get_video_properties(self):
        if self.video_codec is None:
            self.get_specs()
        return {'file_size':self.filesize, opt.media.FORMAT: self.format, opt.media.VBITRATE: self.video_bitrate, \
        opt.media.VCODEC: self.video_codec, opt.media.FPS:self.video_fps, \
        'width':self.width, 'height': self.height, opt.media.ASPECT: self.aspect, \
        'pixel_aspect_ratio': self.pixel_aspect,'author': self.author, \
        'copyright': self.copyright, 'year':self.year }

    def get_properties(self):
        all_props = self.get_file_properties()
        util.logger.debug("File properties(%s) = %s", self.filename, str(all_props))
        all_props.update(self.get_audio_properties())
        util.logger.debug("After audio properties(%s) = %s", self.filename, str(all_props))
        all_props.update(self.get_video_properties())
        util.logger.debug("After video properties(%s) = %s", self.filename, str(all_props))
        return all_props

    def crop(self, width, height, top, left, out_file, **kwargs):
        ''' Applies crop video filter for width x height pixels '''

        if width is str:
            width = int(width)
        if height is str:
            height = int(height)
        i_bitrate = self.get_video_bitrate()
        i_w, i_h = self.get_dimensions()
        media_opts = self.get_properties()
        media_opts[opt.media.ACODEC] = 'copy'
        # Target bitrate proportional to crop level (+ 20%)
        media_opts[opt.media.VBITRATE] = int(int(i_bitrate) * (width * height) / (int(i_w) * int(i_h)) * 1.2)

        media_opts.update(util.cleanup_options(kwargs))
        util.logger.info("Cmd line settings = %s", str(media_opts))
        out_file = util.automatic_output_file_name(out_file, self.filename, \
            "crop_{0}x{1}-{2}x{3}".format(width, height, top, left))
        aspect = __get_aspect_ratio__(width, height, **kwargs)


        cmd = '-i "%s" %s %s -aspect %s "%s"' % (self.filename, \
            media.build_ffmpeg_options(media_opts), media.get_crop_filter_options(width, height, top, left), \
            aspect, out_file)
        util.run_ffmpeg(cmd)
        return out_file

    def cut(self, start, stop, fade=None, out_file=None):
        if out_file is None:
            out_file = util.automatic_output_file_name(
                out_file, self.filename,
                "cut_%s_to_%s" % (start.replace(':','-'), stop.replace(':','-')))
        util.logger.debug("Cutting %s from %s to %s into %s", self.filename, start, stop, out_file)
        # media_opts = self.get_properties()
        media_opts = {
            opt.media.START: start,
            opt.media.STOP: stop,
            opt.media.VCODEC: 'copy',
            opt.media.ACODEC: 'copy'
        }
        video_filters = []
        if fade is not None:
            fmt = "fade=type={0}:duration={1}:start_time={2}"
            fader = fmt.format('in', fade, util.to_seconds(start)) + "," + fmt.format('out', fade, util.to_seconds(stop) - fade)
            video_filters.append(fader)
        util.run_ffmpeg('-i "%s" %s %s "%s"' % (self.filename, media.build_ffmpeg_options(media_opts),
                                                media.build_video_filters_options(video_filters), out_file))

        return out_file

    def add_metadata(self, **metadatas):
        # ffmpeg -i in.mp4 -vcodec copy -c:a copy -map 0 -metadata year=<year>
        # -metadata copyright="(c) O. Korach <year>"  -metadata author="Olivier Korach"
        # -metadata:s:a:0 language=fre -metadata:s:a:0 title="Avec musique"
        # -metadata:s:v:0 language=fre -disposition:a:0 default -disposition:a:1 none "%~1.meta.mp4"
        util.logger.debug("Add metadata: %s", str(metadatas))
        opts = VideoFile.AV_PASSTHROUGH
        for key, value in metadatas.items():
            opts += '-metadata {0}="{1}" '.format(key, value)
        output_file = util.add_postfix(self.filename, "meta")
        util.run_ffmpeg(FFMPEG_CLASSIC_FMT.format(self.filename, opts.strip(), output_file))
        return output_file

    def set_default_track(self, track):
        # ffmpeg -i in.mp4 -vcodec copy -c:a copy -map 0
        # -disposition:a:0 default -disposition:a:1 none out.mp4
        util.logger.debug("Set default track: %s", track)
        disp = VideoFile.AV_PASSTHROUGH
        for i in range(self.__get_number_of_audio_tracks()+1):
            util.logger.debug("i = %d, nb tracks = %d", i, self.__get_number_of_audio_tracks())
            is_default = "default" if i == track else "none"
            disp += "-disposition:a:{0} {1} ".format(i, is_default)
        output_file = util.add_postfix(self.filename, "track")
        util.run_ffmpeg(FFMPEG_CLASSIC_FMT.format(self.filename, disp.strip(), output_file))
        return output_file

    def set_tracks_property(self, prop, **props):
        util.logger.debug("Set tracks properties: %s-->%s", prop, str(props))
        meta = VideoFile.AV_PASSTHROUGH
        for idx, propval in props.items():
            meta += '-metadata:s:a:{0} {1}="{2}" '.format(idx, prop, propval)
        output_file = util.add_postfix(self.filename, prop)
        util.run_ffmpeg(FFMPEG_CLASSIC_FMT.format(self.filename, meta.strip(), output_file))
        return output_file

    def set_tracks_language(self, **langs):
        # ffmpeg -i in.mp4 -vcodec copy -c:a copy -map 0
        # -metadata:s:a:0 language=fre -metadata:s:a:1 language=eng out.mp4
        return self.set_tracks_property("language", **langs)

    def set_tracks_title(self, **titles):
        # ffmpeg -i in.mp4 -vcodec copy -c:a copy -map 0
        # -metadata:s:a:0 title="Avec musique" -metadata:s:a:1 title="Anglais" out.mp4
        return self.set_tracks_property("title", **titles)

    def add_copyright(self, copyr, year = None):
        if year is None:
            import datetime
            year = datetime.datetime.now().year
        return self.add_metadata(**{'copyright': '© {0} {1}'.format(copyr ,year)})

    def add_stream_property(self, stream_index, prop, value = None):
        direct_copy = '-vcodec copy -c:a copy -map 0'
        output_file = util.add_postfix(self.filename, "meta")
        if value is None:
            stream_index, value = stream_index.split(':')
        util.run_ffmpeg('-i "{0}" {1} -metadata:s:a:{2} {3}="{4}" "{5}"'.format( \
            self.filename, direct_copy, stream_index, prop, value, output_file))
        return output_file

    def add_stream_language(self, stream_index, language = None):
        return self.add_stream_property(stream_index, 'language', language)

    def add_stream_title(self, stream_index, title = None):
        return self.add_stream_property(stream_index, 'title', title)

    def add_author(self, author):
        return self.add_metadata(**{'author': author})

    def add_year(self, year):
        return self.add_metadata(**{'year': year})

    def add_audio_tracks(self, *audio_files):
        inputs = '-i "{0}"'.format(self.filename)
        maps = '-map 0'
        i = 1
        for audio_file in audio_files:
            inputs += ' -i "{0}"'.format(audio_file)
            maps += ' -map {0}'.format(i)
            i += 1
        output_file = util.add_postfix(self.filename, "muxed")
        util.run_ffmpeg('{0} {1} -dn -codec copy "{2}"'.format(inputs, maps, output_file))
        return output_file

    def deshake(self, width, height, out_file, **kwargs):
        ''' Applies deshake video filter for width x height pixels '''
        media_opts = self.get_properties()
        media_opts.update({opt.media.DEINTERLACE:None, opt.media.ASPECT:self.get_aspect_ratio()})
        media_opts.update(util.cleanup_options(kwargs))

        if out_file is None or 'nocrop' in kwargs:
            output_file = util.add_postfix(self.filename, "deshake_%dx%d" % (width, height))
        else:
            output_file = out_file

        ffopts = opt.media2ffmpeg(media_opts)
        cmd = '-i "%s" %s %s "%s"' % (self.filename, \
            util.dict2str(ffopts), get_deshake_filter_options(width, height), output_file)
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
        kwargs.update({opt.media.ASPECT: self.get_aspect_ratio()})
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

    def reverse(self, out_file=None, with_audio=False, **kwargs):
        (w, _) = self.get_dimensions()
        if w >= 1920:
            profile = "1080p"
        elif w >= 1280:
            profile = "720p"
        else:
            profile = "540p"
        out_file = util.automatic_output_file_name(out_file, self.filename, 'reverse', extension="mp4")
        kwargs.pop('hw_accel', None)
        return self.encode(out_file, profile, reverse=True, audio_reverse=False, **kwargs)


    def encode(self, target_file, profile, **kwargs):
        '''Encodes a file
        - target_file is the name of the output file. Optional
        - Profile is the encoding profile as per the VideoTools.properties config file
        - **kwargs accepts at large panel of other ptional options'''

        util.logger.debug("Encoding %s with profile %s and args %s", self.filename, profile, str(kwargs))
        if target_file is None:
            target_file = media.build_target_file(self.filename, profile)

        media_opts = {}
        video_filters = []
        audio_filters = []
        media_opts = self.get_properties()
        util.logger.debug("File settings(%s) = %s", self.filename, str(media_opts))
        media_opts.update(util.get_ffmpeg_cmdline_params(util.get_conf_property(profile + '.cmdline')))
        util.logger.debug("After profile settings(%s) = %s", profile, str(media_opts))
        media_opts.update(kwargs)
        util.logger.debug("After cmd line settings(%s) = %s", str(kwargs), str(media_opts))

        media_opts['input_params'] = ''
        if 'hw_accel' in kwargs and kwargs['hw_accel'] is True:
            if re.search(r'[xh]264', media_opts[opt.media.VCODEC]):
                util.logger.debug("Patching settings for H264 hw acceleration")
                media_opts[opt.media.VCODEC] = 'h264_nvenc'
                media_opts['input_params'] = '-hwaccel cuvid -c:v h264_cuvid'
            elif re.search(r'[xh]265', media_opts[opt.media.VCODEC]):
                util.logger.debug("Patching settings for H265 hw acceleration")
                media_opts[opt.media.VCODEC] = 'hevc_nvenc'
                media_opts['input_params'] = '-hwaccel cuvid -c:v h264_cuvid'
            if media_opts['input_params'] != '' and opt.media.SIZE in media_opts and media_opts[opt.media.SIZE] is not None:
                media_opts['input_params'] += ' -resize ' + media_opts[opt.media.SIZE]
                del media_opts[opt.media.SIZE]

        util.logger.debug("After hw acceleration = %s", str(media_opts))

        ffopts = opt.media2ffmpeg(media_opts)
        util.logger.debug("After converting to ffmpeg params = %s", str(ffopts))

        # Hack for channels selection
        mapping = __get_audio_channel_mapping__(**kwargs)

        video_filters.append(self.__get_reverse_filter__(**kwargs))
        audio_filters.append(self.__get_reverse_audio_filter__(**kwargs))
        video_filters.append(self.__get_fader_filter__(**kwargs))

        util.run_ffmpeg('%s -i "%s" %s %s %s "%s"' % (media_opts['input_params'], self.filename, util.dict2str(ffopts), \
                        media.build_video_filters_options(video_filters, audio_filters), mapping, target_file))
        util.logger.info("File %s encoded", target_file)
        return target_file

    #------------------ Private methods ------------------------------------------


    def __get_reverse_filter__(self, **kwargs):
        if kwargs.get('reverse', False):
            return 'reverse'
        return None

    def __get_reverse_audio_filter__(self, **kwargs):
        if kwargs.get('audio_reverse', False):
            return 'areverse'
        return None

    def __get_fader_filter__(self, **kwargs):
        if 'fade' in kwargs and kwargs['fade'] is not None:
            fade_d = int(kwargs['fade'])
            start = util.to_seconds(kwargs['start']) if 'start' in kwargs else 0
            stop = util.to_seconds(kwargs['stop']) if 'stop' in kwargs else float(self.get_duration())
            fmt = "fade=type={0}:duration={1}:start_time={2}"
            return fmt.format('in', fade_d, start) + "," + fmt.format('out', fade_d, stop-fade_d)
        return None

    def __get_number_of_audio_tracks(self):
        n = 0
        for stream in self.specs['streams']:
            if stream['codec_type'] != 'audio':
                n += 1
        return n

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


def get_crop_filter_options(width, height, top, left):
    # ffmpeg -i in.mp4 -filter:v "crop=out_w:out_h:x:y" out.mp4
    return "-filter:v crop={0}:{1}:{2}:{3}".format(width, height, top, left)

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

def concat(target_file, file_list, with_audio=True):
    '''Concatenates several video files - They must have same video+audio format and bitrate'''
    util.logger.info("%s = %s", target_file, ' + '.join(file_list))
    cmd = ''
    for file in file_list:
        cmd += (' -i "%s" ' % file)
    count = 0
    cmd += '-filter_complex "'
    for file in file_list:
        cmd += "[{}:v]".format(count)
        if with_audio:
            cmd += "[{}:a]".format(count)
        count += 1

    audio_patch = ''
    audio_patch2 = ''
    if with_audio:
        audio_patch = 'a=1'
        audio_patch2 = '[outa]'
    cmd += 'concat=n={}:v=1:{}[outv]{}" -map "[outv]"'.format(count, audio_patch, audio_patch2)
    if with_audio:
        cmd += ' -map "[outa]"'

    cmd += ' "{}"'.format(target_file)
    util.run_ffmpeg(cmd.strip())
    return target_file

def add_video_args(parser):
    """Parses options specific to video encoding scripts"""
    parser.add_argument('-p', '--profile', required=False, help='Profile to use for encoding')

    parser.add_argument('--' + opt.media.VCODEC, required=False, help='Video codec (h264, h265, mp4, mpeg2, xvid...)')
    parser.add_argument('--' + opt.media.ACODEC, required=False, help='Audio codec (mp3, aac, ac3...)')

    parser.add_argument('--hw_accel', required=False, dest='hw_accel', action='store_true', \
                        help='Use Nvidia HW acceleration')

    parser.add_argument('--' + opt.media.VBITRATE, required=False, help='Video bitrate eg 1024k')
    parser.add_argument('--' + opt.media.ABITRATE, required=False, help='Audio bitrate eg 128k')

    parser.add_argument('--fade', required=False, help='Fade in/out duration')

    parser.add_argument('-t', '--timeranges', required=False, help='Ranges of encoding <start>:<end>,<start>:<end>')
    parser.add_argument('--' + opt.media.START, required=False, help='Start time')
    parser.add_argument('--' + opt.media.STOP, required=False, help='Stop time')

    parser.add_argument('-f', '--' + opt.media.FORMAT, required=False, help='Output file format eg mp4')
    parser.add_argument('-r', '--' + opt.media.FPS, required=False, help='Video framerate of the output eg 25')


    parser.add_argument('--asampling', required=False, help='Audio sampling eg 44100')
    parser.add_argument('--' + opt.media.ACHANNEL, required=False, help='Audio channel to pick')

    parser.add_argument('--' + opt.media.SIZE, required=False, help='Video size HxW')
    parser.add_argument('--' + opt.media.WIDTH, required=False, help='Video width')
    parser.add_argument('--vheight', required=False, help='Video height')

    return parser

def __get_aspect_ratio__(width, height, **kwargs):
    if kwargs.get('aspect', None) is None:
        aw, ah = re.split(":", media.reduce_aspect_ratio(width, height))
    else:
        aw, ah = re.split(":", kwargs['aspect'])
    return "{0}:{1}".format(aw, ah)

def __get_audio_channel_mapping__(**kwargs):
    # Hack for channels selection
    if kwargs.get('achannels', None) is None:
        return ''
    mapping = "-map 0:v:0"
    mapping += ' '.join(list(map(lambda x: '-map 0:a:{}'.format(x), kwargs['achannels'].split(','))))
    return mapping


def build_slideshow(input_files, outfile="slideshow.mp4", resolution=None, **kwargs):
    util.logger.debug("%s = slideshow(%s)", outfile, " + ".join(input_files))
    if resolution is None:
        resolution = VideoFile.DEFAULT_RESOLUTION

    transition_duration = 0.5
    fade_in = filters.fade_in(duration=transition_duration)

    pixfmt = filters.format('yuva420p')
    nb_files = len(input_files)

    total_duration = 0
    vfiles = list(map(lambda f: VideoFile(f), input_files))
    cfilters = []
    for i in range(nb_files):
        f = vfiles[i]
        fade_out = filters.fade_out(start=f.duration - transition_duration, duration=vfiles[i].duration)
        total_duration += f.duration
        pts = filters.setpts("PTS-STARTPTS+{}/TB".format(i*(f.duration-transition_duration)))
        cfilters.append(filters.wrap_in_streams((pixfmt, fade_in, fade_out, pts), str(i) + ':v', 'faded' + str(i)))

    # Add fake input for the trim filter
    input_files.append(input_files[0])

    trim_f = filters.trim(duration=total_duration - transition_duration * (nb_files - 1))
    cfilters.append(filters.wrap_in_streams(trim_f, str(nb_files) + ':v', 'trim'))
    for i in range(nb_files):
        in_stream = 'trim' if i == 0 else 'over' + str(i)
        cfilters.append(filters.overlay(in_stream, 'faded' + str(i), 'over' + str(i + 1)))
    cfilters.append(filters.wrap_in_streams(filters.setsar("1:1"), "over{}".format(nb_files), "final"))

    inputs = ' \\\n'.join(list(map(lambda f: '-i "{}"'.format(f), input_files)))
    filtercomplex = '-filter_complex "\\\n{}"'.format('; \\\n'.join(cfilters))
    util.run_ffmpeg("{} \\\n{} \\\n{} -map [final] {} -s {} {}".format(
        filters.hw_accel_input(**kwargs), inputs, filtercomplex,
        filters.hw_accel_output(**kwargs), resolution, outfile))
    return outfile

#            ffmpeg -i 1.mp4 -i 2.mp4 -f lavfi -i color=black -filter_complex \
#[0:v]format=pix_fmts=yuva420p,fade=t=out:st=4:d=1:alpha=1,setpts=PTS-STARTPTS[va0];\
#[1:v]format=pix_fmts=yuva420p,fade=t=in:st=0:d=1:alpha=1,setpts=PTS-STARTPTS+4/TB[va1];\
#[2:v]scale=960x720,trim=duration=9[over];\
#[over][va0]overlay[over1];\
#[over1][va1]overlay=format=yuv420[outv]" \
#-vcodec libx264 -map [outv] out.mp4


def slideshow(image_files, resolution="1920x1080"):
    MAX_SLIDESHOW_AT_ONCE = 30
    video_files = []
    all_video_files = []
    slideshows = []
    for imgfile in image_files:
        if util.is_image_file(imgfile):
            try:
                video_files.append(image.ImageFile(imgfile).to_video(with_effect=True, resolution=resolution))
            except OSError:
                util.logger.error("Failed to use %s for slideshow, skipped", imgfile)
        elif util.is_video_file(imgfile):
            video_files.append(imgfile)
        else:
            continue
        if len(video_files) >= MAX_SLIDESHOW_AT_ONCE:
            slideshows.append(build_slideshow(video_files, resolution=resolution,
                outfile='slideshow.part{}.mp4'.format(len(slideshows))))
            all_video_files.append(video_files)
            video_files = []
    if len(all_video_files) == 0:
        return build_slideshow(video_files, resolution=resolution, outfile='slideshow.mp4')
    else:
        slideshows.append(build_slideshow(video_files, resolution=resolution,
            outfile='slideshows.{}.mp4'.format(len(slideshows))))
        return concat(target_file='slideshow.mp4', file_list=slideshows, with_audio=False)