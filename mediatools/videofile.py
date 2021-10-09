#!python3
#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

'''Video file tools'''

from __future__ import print_function
import re
import os
import subprocess
from mediatools import log
import mediatools.exceptions as ex
import mediatools.resolution as res
import mediatools.utilities as util
import mediatools.file as fil
import mediatools.mediafile as media
import mediatools.imagefile as image
import mediatools.options as opt
from mediatools import filters
import mediatools.media_config as conf

FFMPEG_CLASSIC_FMT = '-i "{0}" {1} "{2}"'
HW_ACCEL = None
HW_ACCEL_PREFIX = "-hwaccel cuda -hwaccel_output_format cuda"

class VideoFile(media.MediaFile):
    AV_PASSTHROUGH = '-{0} copy -{1} copy -map 0 '.format(opt.OptionFfmpeg.VCODEC, opt.OptionFfmpeg.ACODEC)

    '''Video file abstraction'''
    def __init__(self, filename):
        if not fil.is_video_file(filename):
            raise ex.FileTypeError(file=filename, expected_type='video')

        self.aspect = None
        self.video_codec = None
        self.video_bitrate = None
        self.resolution = None
        self.duration = None
        self.video_fps = None
        self.pixel_aspect = None
        self.audio_bitrate = None
        self.audio_codec = None
        self.audio_language = None
        self.audio_sample_rate = None
        self.year = None
        super().__init__(filename)
        self.get_specs()

    def get_specs(self):
        '''Returns video file complete specs as dict'''
        # if self.specs is None:
        self.probe()
        self.decode_specs()

    def decode_specs(self):
        self.get_file_specs()
        self.get_video_specs()
        self.get_audio_specs()

    def get_video_specs(self):
        '''Returns video file video specs as dict'''
        stream = self.__get_first_video_stream__()
        _, _ = self.dimensions(stream)
        _ = self.get_fps(stream)
        _ = self.get_video_codec(stream)
        _ = self.get_pixel_aspect_ratio(stream)
        self.video_bitrate = int(stream.get('bit_rate', 0))
        if self.video_bitrate == 0:
            try:
                self.video_bitrate = self.specs['format']['bit_rate']
            except KeyError:
                log.logger.error("Can't find video_bitrate in %s", str(self.specs))
        self.duration = round(float(stream.get('duration', 0)), 3)
        if self.duration == 0.0:
            log.logger.error("Can't find duration in %s", str(stream))
        try:
            self.copyright = self.specs['format']['tags']['copyright']
            log.logger.info("%s copyright = %s", self.filename, self.copyright)
        except KeyError:
            log.logger.info("%s has no copyright", self.filename)
        return self.specs

    def get_audio_specs(self):
        '''Returns video file audio specs as dict'''
        for stream in self.specs['streams']:
            if stream['codec_type'] != 'audio':
                continue
            self.audio_codec = self.__get_audio_stream_attribute__('codec_name', stream)
            self.audio_bitrate = self.__get_audio_stream_attribute__('bit_rate', stream)
            self.audio_sample_rate = self.__get_audio_stream_attribute__('sample_rate', stream)
            if 'tags' in stream and 'language' in stream['tags']:
                self.audio_language = stream['tags']['language']
                if self.audio_bitrate is None:
                    self.audio_bitrate = stream['tags']['BPS-eng']
                if self.audio_language in util.LANGUAGE_MAPPING:
                    self.audio_language = util.LANGUAGE_MAPPING[self.audio_language]
            if self.audio_bitrate is not None:
                self.audio_bitrate = int(self.audio_bitrate)
            break
        return self.specs

    def get_aspect_ratio(self):
        '''Returns video file aspect ratio'''
        if self.aspect is None:
            self.get_specs()
        return self.aspect

    def get_pixel_aspect_ratio(self, stream=None):
        '''Returns video file pixel aspect ratio'''
        if self.pixel_aspect is None:
            ar = stream.get('display_aspect_ratio', None)
            if ar is None:
                ar = "%d:%d" % (self.get_width(), self.get_height())
            self.aspect = media.reduce_aspect_ratio(ar)
            par = stream.get('sample_aspect_ratio', None)
            if par is None:
                par = media.reduce_aspect_ratio("%d:%d" % (self.get_width(), self.get_height()))
            self.pixel_aspect = media.reduce_aspect_ratio(par)
        return self.pixel_aspect

    def get_video_codec(self, stream):
        '''Returns video file video codec'''
        log.logger.debug('Getting video codec')
        if self.video_codec is not None:
            return self.video_codec
        if stream is None:
            stream = self.__get_first_video_stream__()
        self.video_codec = stream.get('codec_name', '')
        if self.video_codec == '':
            log.logger.error("Can't find video codec in stream %s\n", util.json_fmt(stream))
        return self.video_codec

    def get_video_duration(self):
        if self.duration is None:
            self.duration = round(float(self.__get_video_stream_attribute__('duration')), 3)
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

    def get_fps(self, stream=None):
        if self.video_fps is None:
            if stream is None:
                stream = self.__get_first_video_stream__()
                log.logger.debug('Video stream is %s', util.json_fmt(stream))
            for tag in ['avg_frame_rate', 'r_frame_rate']:
                if tag in stream:
                    self.video_fps = media.compute_fps(stream[tag])
                    break
        return self.video_fps

    def dimensions(self, stream=None, ignore_orientation=True):
        log.logger.debug('Getting video dimensions')
        if self.resolution is None:
            if stream is None:
                stream = self.__get_first_video_stream__()
            w = int(util.get_first_value(stream, ('width', 'codec_width', 'coded_width')))
            h = int(util.get_first_value(stream, ('height', 'codec_height', 'coded_height')))
            self.resolution = res.Resolution(width=w, height=h)
        log.logger.debug("Resolution = %s", str(self.resolution))
        return (self.resolution.width, self.resolution.height)

    def get_height(self):
        if self.resolution is None:
            _, _ = self.dimensions()
        return self.resolution.height

    def get_width(self):
        if self.resolution is None:
            _, _ = self.dimensions()
        return self.resolution.width

    def get_resolution(self):
        if self.resolution is None:
            _, _ = self.dimensions()
        return self.resolution

    def calc_resolution(self, w, h):
        return self.resolution.calc_resolution(w, h)

    def get_audio_properties(self):
        if self.audio_codec is None:
            self.get_specs()
        return {
            opt.Option.ABITRATE: self.audio_bitrate, opt.Option.ACODEC: self.audio_codec,
            'audio_language': self.audio_language, 'audio_sample_rate': self.audio_sample_rate
        }

    def get_video_properties(self):
        if self.video_codec is None:
            self.get_specs()
        return {
            'file_size': self.size, opt.Option.FORMAT: self.format, opt.Option.VBITRATE: self.video_bitrate,
            opt.Option.VCODEC: self.video_codec, opt.Option.FPS: self.video_fps,
            'width': self.get_width(), 'height': self.get_height(), opt.Option.ASPECT: self.aspect,
            'pixel_aspect_ratio': self.pixel_aspect, 'author': self.author,
            'copyright': self.copyright, 'year': self.year
        }

    def get_properties(self):
        all_props = self.get_file_properties()
        all_props.update(self.get_audio_properties())
        all_props.update(self.get_video_properties())
        all_props = all_props.copy()
        all_props['resolution'] = str(all_props['resolution'])
        log.logger.debug("Properties(%s) = %s", self.filename, str(all_props))
        return all_props

    def crop(self, out_file=None, **kwargs):
        ''' Applies crop video filter for width x height pixels '''
        width, height = kwargs.pop('width'), kwargs.pop('height')
        media_opts = self.get_properties()
        media_opts[opt.Option.ACODEC] = 'copy'
        (width, height) = self.calc_resolution(width, height)
        (top, left, pos) = self.__get_top_left__(width=width, height=height, **kwargs)

        # Target bitrate proportional to crop level (x 2)
        media_opts[opt.Option.VBITRATE] = int(self.video_bitrate * width * height / self.resolution.pixels * 2)

        media_opts.update(util.cleanup_options(kwargs))
        media_opts[opt.Option.RESOLUTION] = "{}x{}".format(width, height)
        log.logger.debug("Cmd line settings = %s", str(media_opts))
        out_file = util.automatic_output_file_name(out_file, self.filename,
            "crop_{0}x{1}-{2}".format(width, height, pos))
        aspect = __get_aspect_ratio__(width, height, **kwargs)

        cmd = '-i "{}" {} -vf "{}" -aspect {} "{}"'.format(self.filename,
            media.build_ffmpeg_options(media_opts), filters.crop(width, height, left, top),
            aspect, out_file)
        util.run_ffmpeg(cmd, self.duration)
        return out_file

    def add_metadata(self, **metadatas):
        # ffmpeg -i in.mp4 -vcodec copy -c:a copy -map 0 -metadata year=<year>
        # -metadata copyright="(c) O. Korach <year>"  -metadata author="Olivier Korach"
        # -metadata:s:a:0 language=fre -metadata:s:a:0 title="Avec musique"
        # -metadata:s:v:0 language=fre -disposition:a:0 default -disposition:a:1 none "%~1.meta.mp4"
        log.logger.debug("Add metadata: %s", str(metadatas))

        options = [filters.vcodec('copy'), filters.acodec('copy')]

        # Handle copyright, author, year
        for key, value in metadatas.items():
            if key in ('author', 'year'):
                options.append(filters.metadata(key, value))
            if key == 'copyright':
                options.append(filters.metadata(key, '© {}'.format(value)))

        nb_tracks = self.__get_number_of_audio_tracks()
        # Handle default_track
        if 'default_track' in metadatas:
            options.append(filters.disposition(metadatas['default_track'], nb_tracks))

        if 'language' in metadatas:
            for m in metadatas['language']:
                try:
                    track, value, details = m.split(':', maxsplit=3)
                    options.append(filters.metadata('language', value, track))
                    options.append(filters.metadata('title', details, track))
                except ValueError:
                    track, value = m.split(':', maxsplit=2)
                    options.append(filters.metadata('language', value, track))

        output_file = util.add_postfix(self.filename, "meta")
        util.run_ffmpeg(f'-i "{self.filename}" -map 0 {filters.format_options(options)} "{output_file}"', self.duration)
        return output_file

    def add_stream_property(self, stream_index, prop, value=None):
        direct_copy = '-vcodec copy -c:a copy -map 0'
        output_file = util.add_postfix(self.filename, "meta")
        if value is None:
            stream_index, value = stream_index.split(':')
        util.run_ffmpeg(f'-i "{self.filename}" {direct_copy} -metadata:s:a:{stream_index} {prop}="{value}" "{output_file}"', self.duration)
        return output_file

    def add_stream_language(self, stream_index, language=None):
        return self.add_stream_property(stream_index, 'language', language)

    def add_stream_title(self, stream_index, title=None):
        return self.add_stream_property(stream_index, 'title', title)

    def add_author(self, author):
        return self.add_metadata(author=author)

    def add_year(self, year):
        return self.add_metadata(year=year)

    def add_audio_tracks(self, *audio_files, out_file=None):
        inputs = '-i "{0}"'.format(self.filename)
        maps = '-map 0'
        i = 1
        for audio_file in audio_files:
            inputs += ' -i "{0}"'.format(audio_file)
            maps += ' -map {0}'.format(i)
            i += 1
        out_file = util.automatic_output_file_name(outfile=out_file, infile=self.filename, postfix='muxed')
        util.run_ffmpeg(f'{inputs} {maps} -dn -codec copy "{out_file}"', self.duration)
        return out_file

    def set_author(self, author):
        self.author = author

    def get_author(self):
        return self.author

    def set_copyright(self, copyr):
        self.copyright = copyr

    def get_copyright(self):
        return self.copyright

    def encode(self, target_file=None, profile=None, **kwargs):
        '''Encodes a file
        - target_file is the name of the output file. Optional
        - Profile is the encoding profile as per the VideoTools.properties config file
        - **kwargs accepts at large panel of other optional options'''
        kwargs = util.get_all_options(**kwargs)
        log.logger.debug("Encoding %s with profile %s and args %s", self.filename, profile, str(kwargs))
        if target_file is None:
            target_file = media.build_target_file(self.filename, profile)

        input_settings = self.__get_input_settings__(**kwargs)
        prefilter_settings = self.__get_prefilter_settings__(**kwargs)
        video_filters = self.__get_video_filters__(**kwargs)
        audio_filters = self.__get_audio_filters__(**kwargs)
        raw_settings = util.get_profile_params(profile)
        log.logger.debug("Profile settings = %s", str(raw_settings))
        output_settings = self.__get_output_settings__(**kwargs)

        # Hack for channels selection
        # mapping = __get_audio_channel_mapping__(**kwargs)
        mapping = ''

        raw_params = ''
        for k, v in raw_settings.items():
            if v is None:
                raw_params += ' ' + str(k)
            else:
                raw_params += ' ' + str(k) + ' ' + str(v)
        if profile is not None and profile.find('mp3') != -1:
            log.logger.info("Encoding mp3 %s", target_file)
            util.run_ffmpeg('{} -i "{}" {} {} {} {} "{}"'.format(
                ' '.join(input_settings), self.filename, raw_params, ' '.join(prefilter_settings),
                str(audio_filters), mapping, target_file), self.duration)
        else:
            util.run_ffmpeg('{} -i "{}" {} {} {} {} {} "{}"'.format(
                ' '.join(input_settings), self.filename, ' '.join(prefilter_settings),
                str(video_filters), str(audio_filters), ' '.join(output_settings),
                mapping, target_file), self.duration)
        log.logger.info("File %s encoded", target_file)
        return target_file

    # ----------------- Private methods ------------------------------------------

    def __get_number_of_audio_tracks(self):
        n = 0
        for stream in self.specs['streams']:
            if stream['codec_type'] != 'audio':
                n += 1
        return n

    def __get_audio_filters__(self, **kwargs):
        log.logger.debug('Afilters options = %s', str(kwargs))
        afilters = filters.Simple(filters.AUDIO_TYPE)
        if kwargs.get('volume', None) is not None:
            vol = util.percent_or_absolute(kwargs['volume'])
            afilters.append(filters.volume(vol))
        if kwargs.get('audio_reverse', False) or kwargs.get('areverse', False):
            afilters.append(filters.areverse())
        log.logger.debug('afilters = %s', str(afilters))
        return afilters

    def __get_video_filters__(self, **kwargs):
        log.logger.debug('Vfilters options = %s', str(kwargs))
        vfilters = filters.Simple(filters.VIDEO_TYPE)
        if kwargs.get('speed', None) is not None:
            vfilters.append(filters.speed(kwargs['speed']))
        if kwargs.get('reverse', False):
            vfilters.append(filters.reverse())
        if 'deshake' in kwargs:
            rx, ry = [int(x) for x in kwargs['deshake'].split('x')]
            vfilters.append(filters.deshake(rx=rx, ry=ry))
            if not kwargs.get('no_crop', False):
                w, h = self.dimensions()
                vfilters.append(filters.crop(w - rx, h - ry, rx // 2, ry // 2))
        if kwargs.get('fade', False):
            vfilters.append(filters.fade_in(start=util.to_seconds(kwargs.get(opt.Option.START, 0)), duration=0.5))
            vfilters.append(filters.fade_out(
                start=util.to_seconds(kwargs.get(opt.Option.STOP, self.duration)) - 0.5, duration=0.5))
        if use_hardware_accel(**kwargs) and kwargs.get(opt.Option.RESOLUTION, None) is not None:
            vfilters.append(f'scale_cuda={kwargs[opt.Option.WIDTH]}:{kwargs[opt.Option.HEIGHT]}')
        log.logger.debug('vfilters = %s', str(vfilters))
        return vfilters

    def __get_input_settings__(self, **kwargs):
        log.logger.debug('Input options = %s', str(kwargs))
        settings = []
        if __must_encode_video__(**kwargs):
            if use_hardware_accel(**kwargs):
                settings.append(HW_ACCEL_PREFIX)
        else:
            if opt.Option.START in kwargs and kwargs[opt.Option.START] != '':
                settings.append(opt.OPT_FMT.format(opt.OptionFfmpeg.START, kwargs[opt.Option.START]))

        log.logger.debug('Input settings = %s', str(settings))
        return settings

    def __get_prefilter_settings__(self, **kwargs):
        settings = []
        return settings

    def __get_output_settings__(self, **kwargs):
        settings = []
        log.logger.debug('Output options = %s', str(kwargs))

        settings.append(__get_vcodec__(**kwargs))
        settings.append(__get_acodec__(**kwargs))

        if kwargs.get(opt.Option.RESOLUTION, None) is not None and not use_hardware_accel(**kwargs):
            settings.append(opt.OPT_FMT.format(opt.OptionFfmpeg.RESOLUTION, kwargs[opt.Option.RESOLUTION]))

        if kwargs.get(opt.Option.VBITRATE, None) is not None:
            settings.append(opt.OPT_FMT.format(opt.OptionFfmpeg.VBITRATE, kwargs[opt.Option.VBITRATE]))

        if kwargs.get(opt.Option.ABITRATE, None) is not None:
            settings.append(opt.OPT_FMT.format(opt.OptionFfmpeg.ABITRATE, kwargs[opt.Option.ABITRATE]))

        if kwargs.get(opt.Option.DEINTERLACE, False):
            settings.append(f'-{opt.OptionFfmpeg.DEINTERLACE}')

        if kwargs.get(opt.Option.STOP, '') != '':
            start = 0
            if kwargs.get(opt.Option.START, '') != '':
                start = util.to_seconds(kwargs[opt.Option.START])
            stop = str(util.to_seconds(kwargs[opt.Option.STOP]) - start)
            settings.append(opt.OPT_FMT.format(opt.OptionFfmpeg.STOP, stop))

        if __must_encode_video__(**kwargs):
            if kwargs.get(opt.Option.START, '') != '':
                settings.append(opt.OPT_FMT.format(opt.OptionFfmpeg.START, kwargs[opt.Option.START]))

            if kwargs.get(opt.Option.STOP, '') != '':
                settings.append(opt.OPT_FMT.format(opt.OptionFfmpeg.STOP, kwargs[opt.Option.STOP]))

        log.logger.debug('Output settings = %s', str(settings))
        return settings

# ---------------- Class methods ---------------------------------


def __get_vcodec__(**kwargs):
    if __must_encode_video__(**kwargs):
        vcodec = kwargs.get(opt.Option.VCODEC, conf.get_property('default.video.codec'))
        if use_hardware_accel(**kwargs):
            vcodec = opt.HW_ACCEL_CODECS[vcodec]
        else:
            vcodec = opt.CODECS[vcodec]
    else:
        vcodec = 'copy'
    if vcodec is None:
        return ''
    else:
        return opt.OPT_FMT.format(opt.OptionFfmpeg.VCODEC, vcodec)


def __get_acodec__(**kwargs):
    acodec = None
    audio_encode = __must_encode_audio__(**kwargs)
    if not audio_encode:
        acodec = 'copy'
    else:
        acodec = kwargs.get(opt.Option.ACODEC, conf.get_property('default.audio.codec'))
    if acodec is None:
        return ''
    else:
        return '-acodec {}'.format(acodec)


def __must_encode_video__(**kwargs):
    for k in kwargs:
        if k in (opt.Option.RESOLUTION, 'speed', opt.Option.VBITRATE, 'width', 'height', 'aspect', 'reverse', 'deshake'):
            return True
        if k == opt.Option.VCODEC and kwargs[k] != 'copy':
            return True
    return False


def __must_encode_audio__(**kwargs):
    for k in kwargs:
        if k in (opt.Option.ACODEC, opt.Option.ABITRATE, 'volume'):
            return True
        if k == opt.Option.ACODEC and kwargs[k] != 'copy':
            return True
    return False


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


def concat(target_file, file_list, with_audio=True):
    '''Concatenates several video files - They must have same video+audio format and bitrate'''
    log.logger.info("%s = %s", target_file, ' + '.join(file_list))
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

    cmd += f' "{target_file}"'
    util.run_ffmpeg(cmd.strip())
    return target_file


def add_video_args(parser):
    """Parses options specific to video encoding scripts"""
    parser.add_argument('-p', '--profile', required=False, help='Profile to use for encoding')

    parser.add_argument('--' + opt.Option.VCODEC, required=False, help='Video codec (h264, h265, mpeg2, xvid...)')
    parser.add_argument('--' + opt.Option.ACODEC, required=False, help='Audio codec (mp3, aac, ac3...)')

    parser.add_argument('--hw_accel', required=False, default=None, dest='hw_accel', action='store_true',
                        help='Use Nvidia HW acceleration')

    parser.add_argument('--' + opt.Option.VBITRATE, required=False, help='Video bitrate eg 1024k')
    parser.add_argument('--' + opt.Option.ABITRATE, required=False, help='Audio bitrate eg 128k')

    parser.add_argument('--fade', required=False, help='Fade in/out duration')

    parser.add_argument('-t', '--timeranges', required=False, help='Ranges of encoding <start>:<end>,<start>:<end>')

    parser.add_argument('-f', '--' + opt.Option.FORMAT, required=False, help='Output file format eg mp4')
    parser.add_argument('-r', '--' + opt.Option.FPS, required=False, help='Video framerate of the output eg 25')

    parser.add_argument('--asampling', required=False, help='Audio sampling eg 44100')
    parser.add_argument('--' + opt.Option.ACHANNEL, required=False, help='Audio channel to pick')
    parser.add_argument('--' + opt.Option.DEINTERLACE, required=False, default=False, dest=opt.Option.DEINTERLACE, action='store_true',
                        help='Deinterlace video')

    return parser


def __get_aspect_ratio__(width, height, **kwargs):
    if kwargs.get('aspect', None) is None:
        aw, ah = re.split(":", media.reduce_aspect_ratio(width, height))
    else:
        aw, ah = re.split(":", kwargs['aspect'])
    return "{0}:{1}".format(aw, ah)


def __get_audio_channel_mapping__(**kwargs):
    # Hack for channels selection
    if opt.Option.ACHANNEL not in kwargs:
        return ''
    mapping = "-map 0:v:0"
    mapping += ' '.join(list(map(lambda x: '-map 0:a:{}'.format(x), str(kwargs[opt.Option.ACHANNEL]).split(','))))
    return mapping


def __build_slideshow__(input_files, outfile="slideshow.mp4", resolution=None, **kwargs):
    log.logger.debug("%s = slideshow(%s)", outfile, " + ".join(input_files))

    transition_duration = float(conf.get_property('default.fade.duration'))
    fade_in = filters.fade_in(duration=transition_duration)

    pixfmt = filters.format('yuva420p')
    nb_files = len(input_files)

    total_duration = 0
    fcomp = filters.Complex(*[VideoFile(f) for f in input_files])
    outs = []
    i = 0
    for f in fcomp.inputs:
        fade_out = filters.fade_out(start=f.duration - transition_duration, duration=f.duration)
        pts = filters.setpts("PTS-STARTPTS+{}/TB".format(total_duration))
        total_duration += f.duration - transition_duration
        last_out = fcomp.add_filtergraph(str(i) + ':v', ','.join([pixfmt, fade_in, fade_out, pts]))
        outs.append(last_out)
        i += 1

    last_out = outs[0]
    for i in range(len(fcomp.inputs) - 1):
        last_out = fcomp.add_filtergraph([last_out, outs[i + 1]], filters.overlay())

    # Add fake input for the trim filter
    fcomp.inputs.append(VideoFile(input_files[0]))
    last_out = fcomp.add_filtergraph(last_out,
        filters.trim(duration=total_duration - transition_duration * (nb_files - 1)))
    last_out = fcomp.add_filtergraph(last_out, filters.setsar("1:1"))

    util.run_ffmpeg(f'{filters.hw_accel_input(**kwargs)} {fcomp.format_inputs()} {str(fcomp)} '
        f'{filters.hw_accel_output(**kwargs)} -s "{resolution}" -map "[{last_out}]" "{outfile}"', total_duration)

    return outfile

    # ffmpeg -i 1.mp4 -i 2.mp4 -f lavfi -i color=black -filter_complex \
    # [0:v]format=pix_fmts=yuva420p,fade=t=out:st=4:d=1:alpha=1,setpts=PTS-STARTPTS[va0];\
    # [1:v]format=pix_fmts=yuva420p,fade=t=in:st=0:d=1:alpha=1,setpts=PTS-STARTPTS+4/TB[va1];\
    # [2:v]scale=960x720,trim=duration=9[over];\
    # [over][va0]overlay[over1];\
    # [over1][va1]overlay=format=yuv420[outv]" \
    # -vcodec libx264 -map [outv] out.mp4


def slideshow(*inputs, resolution=None):
    log.logger.info("slideshow(%s)", str(inputs))
    MAX_SLIDESHOW_AT_ONCE = 30
    slideshow_files = fil.file_list(*inputs)
    video_files = []
    all_video_files = []
    slideshows = []
    slideshow_root_filename = None
    operations = []
    if resolution is None:
        resolution = conf.get_property('default.video.resolution')
    fmt = conf.get_property('default.video.format')

    for slide_file in slideshow_files:
        if fil.is_image_file(slide_file):
            if slideshow_root_filename is None:
                slideshow_root_filename = fil.random_name(slide_file, 'slideshow')
                log.logger.info("Final slideshow file will be %s.%s", slideshow_root_filename, fmt)
            try:
                (out_file, details) = image.ImageFile(slide_file).to_video(with_effect=True, resolution=resolution)
                video_files.append(out_file)
                operations.append(details)
            except OSError:
                log.logger.error("Failed to use %s for slideshow, skipped", slide_file)
        elif fil.is_video_file(slide_file):
            # video_files.append(slide_file)
            log.logger.info("File %s is a video, skipped", slide_file)
        else:
            log.logger.info("File %s is neither an image not a video, skipped", slide_file)
            continue
        if len(video_files) >= MAX_SLIDESHOW_AT_ONCE:
            slideshows.append(__build_slideshow__(video_files, resolution=resolution,
                outfile=f'{slideshow_root_filename}.part{len(slideshows)}.{fmt}'))
            all_video_files.append(video_files)
            video_files = []
    final_file = '{}.{}'.format(slideshow_root_filename, fmt)
    if len(all_video_files) == 0:
        return (
            __build_slideshow__(video_files, resolution=resolution, outfile=final_file),
            operations)
    else:
        slideshows.append(__build_slideshow__(video_files, resolution=resolution,
            outfile=f'{slideshow_root_filename}.part{len(slideshows)}.{fmt}'))
        return (
            concat(target_file=final_file, file_list=slideshows, with_audio=False),
            operations)


def speed(filename, target_speed, output=None, **kwargs):
    output = util.automatic_output_file_name(outfile=output, infile=filename, postfix=f'speed-{target_speed}')
    return VideoFile(filename).encode(speed=target_speed, target_file=output, **kwargs)


def volume(filename, vol, output=None, **kwargs):
    output = util.automatic_output_file_name(outfile=output, infile=filename, postfix='volume')
    return VideoFile(filename).encode(volume=vol, target_file=output, **kwargs)


def reverse(filename, output=None, **kwargs):
    kwargs['hw_accel'] = False  # Reverse filter not compatible with HW accel
    output = util.automatic_output_file_name(outfile=output, infile=filename, postfix='reverse')
    return VideoFile(filename).encode(reverse=True, target_file=output, **kwargs)


def deshake(filename, output=None, **kwargs):
    output = util.automatic_output_file_name(infile=filename, outfile=output, postfix='deshake')
    return VideoFile(filename).encode(target_file=output, **kwargs)


def cut(filename, output=None, start=None, stop=None, timeranges=None, **kwargs):
    ''' Args: start and/or stop or timeranges '''
    if 'vcodec' not in kwargs:
        kwargs['vcodec'] = 'copy'
        kwargs['hw_accel'] = False
    if 'acodec' not in kwargs:
        kwargs['acodec'] = 'copy'
        kwargs['hw_accel'] = False
    if kwargs['acodec'] == 'copy' or kwargs['vcodec'] == 'copy':
        for o in ('abitrate', 'vbitrate', 'fps', 'aspect', 'resolution', 'achannels', 'samplerate', 'width', 'height'):
            kwargs.pop(o, None)

    if start is None and stop is None:
        i = 1
        for r in timeranges.split(','):
            kwargs['start'], kwargs['stop'] = r.split('-', maxsplit=2)
            output = util.automatic_output_file_name(outfile=output, infile=filename, postfix='cut{}'.format(i))
            output = VideoFile(filename).encode(target_file=output, **kwargs)
            util.generated_file(output)
            i += 1
        return output
    else:
        output = util.automatic_output_file_name(outfile=output, infile=filename, postfix='cut')
        return VideoFile(filename).encode(target_file=output, start=start, stop=stop, **kwargs)


def use_hardware_accel(**kwargs):
    global HW_ACCEL
    if 'hw_accel' in kwargs:
        if kwargs['hw_accel']:
            log.logger.info("Hardware acceleration explicitly forced on")
            return True
        elif not kwargs['hw_accel']:
            log.logger.info("Hardware acceleration explicitly turned off")
            return False
    elif kwargs.get(opt.Option.DEINTERLACE, False):
        # Deinterlacing is incompatible with HW accel
        log.logger.info("Turning off hardware acceleration because of deinterlace")
        HW_ACCEL = False
    if HW_ACCEL is not None:
        return HW_ACCEL

    if HW_ACCEL is None:
        log.logger.info("Checking if hardware acceleration can be used")
        outputfile = util.get_tmp_file() + '.mp4'
        inputfile = VideoFile(str(util.package_home() / 'video-720p.mp4'))
        try:
            log.logger.debug("Trying to encode 1 second of %s", inputfile)
            util.run_ffmpeg(f'{HW_ACCEL_PREFIX} -i "{inputfile}" -vf scale_cuda=640:-1 -c:a copy -c:v h264_nvenc "{outputfile}"',
                inputfile.duration)
            os.remove(outputfile)
            HW_ACCEL = True
        except subprocess.CalledProcessError:
            HW_ACCEL = False
        log.logger.info("Hardware acceleration = %s", str(HW_ACCEL))
    return HW_ACCEL
