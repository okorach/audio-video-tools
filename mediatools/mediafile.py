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

from datetime import datetime
import re
from exiftool import ExifToolHelper
import ffmpeg
from mediatools import log
import utilities.file as fil
import mediatools.exceptions as ex
import mediatools.utilities as util
import mediatools.filters as filters
import mediatools.options as opt
import mediatools.media_config as conf

EXIF_LONGITUDE_TAG = "EXIF:GPSLongitude"
EXIF_LONG_REF_TAG = "EXIF:GPSLongitudeRef"
EXIF_LATITUDE_TAG = "EXIF:GPSLatitude"
EXIF_LAT_REF_TAG = "EXIF:GPSLatitudeRef"

EXIF_DATE_FMT = "%Y:%m:%d %H:%M:%S"
ISO_DATE_FMT = "%Y-%m-%d %H:%M:%S"
TIME_FMT = "%H:%M:%S"
DATE_FORMATS = (ISO_DATE_FMT, f"{ISO_DATE_FMT}%z", EXIF_DATE_FMT, f"{EXIF_DATE_FMT}%z")
CREATION_DATE_TAGS = ("QuickTime:CreateDate", "EXIF:DateTimeOriginal", "File:FileModifyDate")


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
        self._exif_data = None
        # self.probe()

    def __str__(self):
        return self.filename

    def __format__(self, format_spec):
        return self.filename

    def probe(self, force=False):
        '''Returns media file general specs'''
        self.stat(force)
        if self.specs is not None and not force:
            return self.specs
        try:
            log.logger.debug('%s(%s)', util.get_ffprobe(), self.filename)
            self.specs = ffmpeg.probe(self.filename, cmd=util.get_ffprobe())
            # log.logger.debug("Specs = %s", util.json_fmt(self.specs))
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
        self.stat()
        d = vars(self)
        d["size"] = d.pop("_size")
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

    def get_exif_data(self, force=False) -> dict[str, str]:
        if self._exif_data is None or force:
            with ExifToolHelper() as et:
                self._exif_data = et.get_metadata(self.filename)[0]
        return self._exif_data

    def set_exif_creation_date(self, some_datetime):
        if type(some_datetime) == datetime:
            time_to_set = datetime.strftime(some_datetime, EXIF_DATE_FMT)
        else:
            time_to_set = some_datetime
        with ExifToolHelper() as et:
            et.set_tags([self.filename], tags={"DateTimeOriginal": time_to_set}, params=["-P", "-overwrite_original"])

    def get_exif_creation_date(self):
        exif_data = self.get_exif_data()
        if "EXIF:DateTimeOriginal" in exif_data:
            str_date = exif_data["EXIF:DateTimeOriginal"]
        elif "File:FileModifyDate" in exif_data:
            str_date = exif_data["File:FileModifyDate"]
        else:
            log.logger.warning("Can't find creation date in %s", util.json_fmt(exif_data))
            return None

        str_date = creation_date = None
        for tag in CREATION_DATE_TAGS:
            if tag in exif_data:
                str_date = exif_data[tag]
                break
        if str_date is None:
            log.logger.warning("Can't find creation date in %s", util.json_fmt(exif_data))
            return None

        if str_date == "0000:00:00 00:00:00":
            str_date = "1900:01:01 00:00:00"

        for fmt in DATE_FORMATS:
            try:
                creation_date = datetime.strptime(str_date, fmt)
            except ValueError:
                continue
        if creation_date is None:
            raise ValueError
        return creation_date

    def get_exif_device(self):
        exif_data = self.get_exif_data()
        device = ""
        for key in "EXIF:Make", "QuickTime:Author", "QuickTime:CompressorName":
            if key in exif_data:
                device = exif_data[key]
                break
        if "EXIF:Model" in exif_data:
            device += " " + exif_data["EXIF:Model"]
        return device

    def get_exif_dimensions(self):
        exif_data = self.get_exif_data()
        for w_key, h_key in (("File:ImageWidth", "File:ImageHeight"), ("EXIF:ExifImageWidth", "EXIF:ExifImageHeight"),
                     ("QuickTime:SourceImageWidth", "QuickTime:SourceImageHeight"), ("QuickTime:ImageWidth", "QuickTime:ImageHeight")):
            if w_key in exif_data and h_key in exif_data:
                dimensions = f'{exif_data[w_key]}x{exif_data[h_key]}'
                break
        if not dimensions:
            dimensions = exif_data.get("Composite:ImageSize", "").replace(" ", "x")
        return dimensions

    def get_exif_gps_coordinates(self):
        (lat, long) = (None, None)
        exif_data = self.get_exif_data()
        if EXIF_LATITUDE_TAG in exif_data:
            lat = exif_data[EXIF_LATITUDE_TAG]
            if exif_data.get(EXIF_LAT_REF_TAG, "N") == "S":
                lat = "-" + lat
        if EXIF_LONGITUDE_TAG in exif_data:
            long = exif_data[EXIF_LONGITUDE_TAG]
            if exif_data.get(EXIF_LONG_REF_TAG, "E") == "W":
                long = "-" + long
        return (float(lat), float(long))

    def set_exif_gps_coordinates(self, latitude, longitude):
        if latitude < 0:
            latitude = -latitude
            lat_ref = "S"
        if longitude < 0:
            longitude = -longitude
            long_ref = "W"
        with ExifToolHelper() as et:
            et.set_tags([self.filename], tags={
                "EXIF:GPSLatitude": latitude,
                "EXIF:GPSLatitudeRef": lat_ref,
                "EXIF:GPSLongitude": longitude,
                "EXIF:GPSLongitudeRef": long_ref
            },
                params=["-P", "-overwrite_original"])


# ---------------- Class methods ---------------------------------

def get_audio_filters(**kwargs):
    log.logger.debug('Afilters options = %s', str(kwargs))
    afilters = filters.Simple(filters.AUDIO_TYPE)
    if kwargs.get('volume', None) is not None:
        vol = util.percent_or_absolute(kwargs['volume'])
        afilters.append(filters.volume(vol))
    if kwargs.get('audio_reverse', False) or kwargs.get('areverse', False):
        afilters.append(filters.areverse())
    log.logger.debug('afilters = %s', str(afilters))
    return afilters


def get_input_settings(**kwargs):
    log.logger.debug('get_input_setting(%s)', str(kwargs))
    settings = []
    if kwargs.get(opt.Option.START, '') != '':
        log.logger.debug("Adding start = %s", str(kwargs[opt.Option.START]))
        settings.append(opt.OPT_FMT.format(opt.OptionFfmpeg.START, kwargs[opt.Option.START]))
    if _must_encode_video(**kwargs) and util.use_hardware_accel(**kwargs):
        settings.append(util.HW_ACCEL_PREFIX)
    log.logger.debug('get_input_settings returns %s', str(settings))
    return settings


def get_prefilter_settings(**kwargs):
    settings = []
    return settings


def get_output_settings(file_type=fil.FileType.VIDEO_FILE, **kwargs):
    settings = {}
    log.logger.debug('get_output_setting(%s)', str(kwargs))

    if file_type == fil.FileType.VIDEO_FILE:
        settings[opt.Option.VCODEC] = _get_vcodec(**kwargs)

        if kwargs.get(opt.Option.RESOLUTION, None) is not None and not util.use_hardware_accel(**kwargs):
            settings[opt.OptionFfmpeg.RESOLUTION] = kwargs[opt.Option.RESOLUTION]

        if kwargs.get(opt.Option.VBITRATE, None) is not None:
            settings[opt.OptionFfmpeg.VBITRATE] = kwargs[opt.Option.VBITRATE]

        if kwargs.get(opt.Option.DEINTERLACE, False):
            settings[opt.OptionFfmpeg.DEINTERLACE] = True

    start = 0
    if kwargs.get(opt.Option.START, None) not in ('', None):
        start = util.to_seconds(kwargs[opt.Option.START])
        # settings[opt.OptionFfmpeg.START] = start
    if kwargs.get(opt.Option.STOP, None) not in ('', None):
        settings[opt.OptionFfmpeg.STOP] = util.to_seconds(kwargs[opt.Option.STOP]) - start

    if kwargs.get(opt.Option.MUTE, False):
        settings[opt.OptionFfmpeg.MUTE] = True
    else:
        settings[opt.Option.ACODEC] = _get_acodec(**kwargs)
        if kwargs.get(opt.Option.ABITRATE, None) is not None:
            settings[opt.OptionFfmpeg.ABITRATE] = kwargs[opt.Option.ABITRATE]
        if kwargs.get(opt.Option.ACODEC, None) is not None:
            settings[opt.OptionFfmpeg.ACODEC] = kwargs[opt.Option.ACODEC]

    if kwargs.get(opt.Option.FPS, None) not in ('', None):
        settings[opt.OptionFfmpeg.FPS] = kwargs[opt.Option.FPS]

    log.logger.debug('get_output_settings returns %s', str(settings))
    return settings


def _must_encode_video(**kwargs):
    for k, v in kwargs.items():
        if k in (opt.Option.RESOLUTION, 'speed', opt.Option.VBITRATE, 'width', 'height', 'aspect', 'reverse', 'deshake'):
            return True
        if k == opt.Option.VCODEC and v != 'copy':
            return True
    return False

def _get_vcodec(**kwargs):
    if _must_encode_video(**kwargs):
        vcodec = kwargs.get(opt.Option.VCODEC, conf.get_property('default.video.codec'))
        if util.use_hardware_accel(**kwargs):
            vcodec = opt.HW_ACCEL_CODECS[vcodec]
        else:
            vcodec = opt.CODECS[vcodec]
    else:
        vcodec = 'copy'
    return vcodec

def _get_acodec(**kwargs):
    acodec = None
    if not _must_encode_audio(**kwargs):
        acodec = 'copy'
    else:
        acodec = kwargs.get(opt.Option.ACODEC, conf.get_property('default.audio.codec'))
    return acodec

def _must_encode_audio(**kwargs):
    for k, v in kwargs.items():
        if k in (opt.Option.ABITRATE, 'volume'):
            return True
        if k == opt.Option.ACODEC and v != 'copy':
            return True
    return False

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


def get_exif_creation_date(filename):
    return MediaFile(filename).get_exif_creation_date()


def set_exif_creation_date(filename, some_datetime):
    MediaFile(filename).set_exif_creation_date(some_datetime)


def get_dimensions(filename):
    return MediaFile(filename).get_dimensions()


def get_exif_gps_coordinates(filename):
    return MediaFile(filename).get_exif_gps_coordinates()


def set_exif_gps_coordinates(filename, latitude, longitude):
    MediaFile(filename).set_exif_gps_coordinates(latitude, longitude)


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


def build_ffmpeg_options(options, with_mapping=False):
    cmd = ''
    for k, v in options.items():
        if with_mapping:
            if k not in opt.M2F_MAPPING:
                log.logger.warning("Option %s can't be mapped to ffmpeg option", str(k))
                continue
            else:
                k = opt.M2F_MAPPING[k]
        if v is None or not v:
            continue
        if v is True:
            cmd = cmd + f" -{k}"
        else:
            cmd = cmd + f' -{k} "{v}"'
    log.logger.debug("Mapped ffmpeg options = %s", cmd)
    return cmd
