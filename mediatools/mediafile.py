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

import re
import ffmpeg
from mediatools import log
import mediatools.file as fil
import mediatools.exceptions as ex
import mediatools.utilities as util
import mediatools.filters as filters
import mediatools.options as opt
import mediatools.media_config as conf


class MediaFile(fil.File):
    '''Media file abstraction
    A media file can be:
    - A video file
    - An audio file
    - An image file'''

    def __init__(self, filename):
        if not fil.is_media_file(filename):
            raise ex.FileTypeError(file=filename)
        super().__init__(filename)
        self.type = fil.get_type(filename)
        self.specs = None
        self.author = None
        self.copyright = None
        self.format = None
        self.duration = None
        self.format_long = None
        self.nb_streams = None
        self.title = None
        self.bitrate = None
        self.comment = None
        self.probe()

    def __str__(self):
        return self.filename

    def __format__(self, format_spec):
        return self.filename

    def probe(self, force=False):
        '''Returns media file general specs'''
        if self.specs is not None and not force:
            return self.specs
        super().probe(force)
        try:
            log.logger.debug('%s(%s)', util.get_ffprobe(), self.filename)
            self.specs = ffmpeg.probe(self.filename, cmd=util.get_ffprobe())
            log.logger.debug("Specs = %s", util.json_fmt(self.specs))
        except ffmpeg.Error as e:
            log.logger.error("%s error: %s", util.get_ffprobe(), e.stderr.decode("utf-8").split("\n")[-2].rstrip())
            raise
        self.get_file_specs()
        return self.specs

    def get_file_specs(self):
        '''Reads file format specs'''
        try:
            fmt = self.specs['format']
        except KeyError as e:
            log.logger.error("JSON %s has no key %s\n", util.json_fmt(self.specs), e.args[0])
        self.format = fmt.get('format_name', None)
        if self.format == 'mov,mp4,m4a,3gp,3g2,mj2':
            ext = self.extension().lower()
            if re.match('^(mp4|mov)', ext):
                self.format = ext

        self.format_long = fmt.get('format_long_name', None)
        self.nb_streams = int(fmt.get('nb_streams', 0))
        if fmt.get('bit_rate', None) is not None:
            self.bitrate = int(fmt.get('bit_rate', 0))
        if fmt.get('duration', None) is not None:
            self.duration = float(fmt.get('duration', 0))

    def get_file_properties(self):
        '''Returns file properties as dict'''
        d = vars(self)
        return d

    def __get_first_video_stream__(self):
        log.logger.debug('Searching first video stream')
        for stream in self.specs['streams']:
            log.logger.debug('Found codec %s / %s', stream['codec_type'], stream['codec_name'])
            if stream['codec_type'] == 'video' and stream['codec_name'] != 'gif':
                return stream
        return None

    def __get_first_audio_stream__(self):
        log.logger.debug('Searching first audio stream')
        return self.__get_stream_by_codec__('codec_type', ('audio'))

    def __get_audio_stream_attribute__(self, attr, stream=None):
        if stream is None:
            stream = self.__get_first_audio_stream__()
        try:
            return stream[attr]
        except KeyError as e:
            log.logger.error("Audio stream %s has no key %s\n", util.json_fmt(stream), e.args[0])
            return None

    def __get_video_stream_attribute__(self, attr, stream=None):
        if stream is None:
            stream = self.__get_first_video_stream__()
        try:
            return stream[attr]
        except KeyError as e:
            log.logger.error("Video stream %s has no key %s\n", util.json_fmt(stream), e.args[0])

    def __get_stream_by_codec__(self, field, codec_list):
        log.logger.debug('Searching stream for codec %s = %s', field, codec_list)
        for stream in self.specs['streams']:
            log.logger.debug('Found codec %s', stream[field])
            if stream[field] in codec_list:
                return stream
        return None

    def get_properties(self):
        all_props = self.get_file_properties()
        return all_props

    def __get_top_left__(self, width, height, **kwargs):
        iw, ih = self.dimensions(ignore_orientation=True)
        top = kwargs.get('top', None)
        left = kwargs.get('left', None)
        pos = kwargs.get('position', None)
        if top is None:
            if pos is None:
                pos = "center"
                top = (ih - height) // 2
            elif re.search('.*top.*', pos):
                top = 0
            elif re.search('.*bottom.*', pos):
                top = ih - height
            else:
                top = (ih - height) // 2
        if left is None:
            if pos is None:
                pos = "center"
                left = (iw - width) // 2
            elif re.search('.*left.*', pos):
                left = 0
            elif re.search('.*right.*', pos):
                left = iw - width
            else:
                left = (iw - width) // 2
        return (top, left, pos)


def build_target_file(source_file, profile):
    extension = util.get_profile_extension(profile)
    if extension is None:
        extension = conf.get_property(f'default.{fil.get_type(source_file)}.format')
    if extension is None:
        extension = fil.extension(source_file)
    return util.add_postfix(source_file, profile, extension)


def get_crop_filter_options(width, height, top, left):
    # ffmpeg -i in.mp4 -filter:v "crop=out_w:out_h:x:y" out.mp4
    return '-filter:v "crop={0}:{1}:{2}:{3}"'.format(width, height, top, left)


def get_deshake_filter_options(width, height):
    # ffmpeg -i <in> -f mp4 -vf deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=16 -b:v 2048k <out>
    return "-vf deshake=x=-1:y=-1:w=-1:h=-1:rx=%d:ry=%d" % (width, height)


def compute_fps(rate):
    ''' Simplifies the FPS calculation '''
    log.logger.debug('Calling compute_fps(%s)', rate)
    if re.match(r"^\d+\/\d+$", rate):
        a, b = [int(x) for x in rate.split('/')]
        return str(round(a / b, 1))
    return rate


def reduce_aspect_ratio(aspect_ratio, height=None):
    ''' Reduces the Aspect ratio calculation in prime factors '''
    if height is None:
        (w, h) = [int(x) for x in re.split("[:/x]", aspect_ratio)]
    else:
        w = aspect_ratio
        h = height
    for n in [2, 3, 5, 7, 11, 13, 17]:
        while w % n == 0 and h % n == 0:
            w = w // n
            h = h // n
    return "%d:%d" % (w, h)


def concat(target_file, file_list):
    #  ffmpeg -i opening.mkv -i episode.mkv -i ending.mkv \
    #  -filter_complex "[0:v] [0:a] [1:v] [1:a] [2:v] [2:a] concat=n=3:v=1:a=1 [v] [a]" \
    #  -map "[v]" -map "[a]" output.mkv
    log.logger.info("Concatenating %s", str(file_list))
    cmd = filters.inputs_str(file_list)
    cmd = cmd + '-filter_complex "'
    for i in range(len(file_list)):
        cmd = cmd + ('[%d:v] [%d:a] ' % (i, i))
    cmd = cmd + 'concat=n=%d:v=1:a=1 [v] [a]" -map "[v]" -map "[a]" %s' % (len(file_list), target_file)
    util.run_ffmpeg(cmd)


def strip_media_options(options):
    strip = {}
    for k in options:
        if k not in opt.M2F_MAPPING:
            strip[k] = options[k]
    log.logger.debug("stripped media options = %s", str(strip))
    return strip


def strip_ffmpeg_options(options):
    strip = {}
    for k in options:
        if k not in opt.F2M_MAPPING:
            strip[k] = options[k]
    log.logger.debug("stripped ffmpeg options = %s", str(strip))
    return strip


def build_ffmpeg_options(options):
    cmd = ''
    for k, v in options.items():
        if options[k] is None or k not in opt.M2F_MAPPING:
            continue
        if options[k] is False:
            continue
        if options[k] is True:
            cmd = cmd + " -%s" % (opt.M2F_MAPPING[k])
        else:
            cmd = cmd + " -%s %s" % (opt.M2F_MAPPING[k], v)
    log.logger.debug("ffmpeg options = %s", cmd)
    return cmd
