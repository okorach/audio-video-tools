#
# media-tools
# Copyright (C) 2019-2026 Olivier Korach
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

"""Media file abstraction (audio, video, image): specs, EXIF data and encoding settings common to all the media files"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

import ffmpeg
from exiftool import ExifToolHelper

import mediatools.exceptions as ex
import mediatools.media_config as conf
import mediatools.options as opt
import mediatools.utilities as util
import utilities.file as fil
from filters import filters
from mediatools import log

if TYPE_CHECKING:
    from collections.abc import Callable

EXIF_LONGITUDE_TAG: str = "EXIF:GPSLongitude"
EXIF_LONG_REF_TAG: str = "EXIF:GPSLongitudeRef"
EXIF_LATITUDE_TAG: str = "EXIF:GPSLatitude"
EXIF_LAT_REF_TAG: str = "EXIF:GPSLatitudeRef"

EXIF_DATE_FMT: str = "%Y:%m:%d %H:%M:%S"
ISO_DATE_FMT: str = "%Y-%m-%d %H:%M:%S"
TIME_FMT: str = "%H:%M:%S"
DATE_FORMATS: tuple[str, ...] = (ISO_DATE_FMT, f"{ISO_DATE_FMT}%z", EXIF_DATE_FMT, f"{EXIF_DATE_FMT}%z")
EXIF_ORIGINAL_DATE_TAG: str = "EXIF:DateTimeOriginal"
FILE_MODIFY_DATE_TAG: str = "File:FileModifyDate"
CREATION_DATE_TAGS: tuple[str, ...] = ("QuickTime:CreateDate", EXIF_ORIGINAL_DATE_TAG, FILE_MODIFY_DATE_TAG)


class MediaFile(fil.File):
    """Media file abstraction
    A media file can be:
    - A video file
    - An audio file
    - An image file"""

    # The media files that have a size (videos and images) implement it
    dimensions: Callable[..., tuple[int, int]]

    def __init__(self, filename: str) -> None:
        """Creates a media file object (audio, video or image). Raises a FileTypeError if the file is not a media file"""
        if not fil.is_media_file(filename):
            raise ex.FileTypeError(file=filename)
        super().__init__(filename)
        self.type: str = fil.get_type(filename)
        self.specs: dict | None = None
        self.author: str | None = None
        self.copyright: str | None = None
        self.format: str | None = None
        self.duration: float | None = None
        self.format_long: str | None = None
        self.nb_streams: int | None = None
        self.title: str | None = None
        self.bitrate: int | None = None
        self.comment: str | None = None
        self._exif_data: dict | None = None

    def __str__(self) -> str:
        """Returns the name of the file"""
        return self.filename

    def __format__(self, format_spec: str) -> str:
        """Returns the name of the file, whatever the format specification"""
        return self.filename

    def probe(self, force: bool = False) -> dict:
        """Returns media file general specs"""
        self.stat(force)
        if self.specs is not None and not force:
            return self.specs
        try:
            log.logger.debug("%s(%s)", util.get_ffprobe(), self.filename)
            self.specs = ffmpeg.probe(self.filename, cmd=util.get_ffprobe())
        except ffmpeg.Error as e:
            log.logger.error("%s error: %s", util.get_ffprobe(), e.stderr.decode("utf-8").split("\n")[-2].rstrip())
            raise
        self.get_file_specs()
        return self.specs

    def get_file_specs(self) -> None:
        """Reads file format specs"""
        try:
            fmt = self.specs["format"]
        except KeyError as e:
            log.logger.error("JSON %s has no key %s\n", util.json_fmt(self.specs), e.args[0])
        self.format = fmt.get("format_name", None)
        if self.format == "mov,mp4,m4a,3gp,3g2,mj2":
            ext = self.extension().lower()
            if re.match("^(mp4|mov)", ext):
                self.format = ext

        self.format_long = fmt.get("format_long_name", None)
        self.nb_streams = int(fmt.get("nb_streams", 0))
        if fmt.get("bit_rate", None) is not None:
            self.bitrate = int(fmt.get("bit_rate", 0))
        if fmt.get("duration", None) is not None:
            self.duration = float(fmt.get("duration", 0))

    def get_file_properties(self) -> dict:
        """Returns file properties as dict"""
        self.stat()
        d = dict(vars(self))  # A copy, to not alter the attributes of the object
        d["size"] = d.pop("_size")
        return d

    def __get_first_video_stream__(self) -> dict | None:
        """Returns the first video stream of the file (a gif is not a video stream), None if there is none"""
        log.logger.debug("Searching first video stream")
        for stream in self.specs["streams"]:
            log.logger.debug("Found codec %s / %s", stream["codec_type"], stream["codec_name"])
            if stream["codec_type"] == "video" and stream["codec_name"] != "gif":
                return stream
        return None

    def __get_first_audio_stream__(self) -> dict | None:
        """Returns the first audio stream of the file, None if there is none"""
        log.logger.debug("Searching first audio stream")
        return self.__get_stream_by_codec__("codec_type", ("audio"))

    def __get_audio_stream_attribute__(self, attr: str, stream: dict | None = None) -> object | None:
        """Returns an attribute of an audio stream (the first one by default), None if the stream does not have it"""
        if stream is None:
            stream = self.__get_first_audio_stream__()
        try:
            return stream[attr]
        except KeyError as e:
            log.logger.error("Audio stream %s has no key %s\n", util.json_fmt(stream), e.args[0])
            return None

    def __get_video_stream_attribute__(self, attr: str, stream: dict | None = None) -> object | None:
        """Returns an attribute of a video stream (the first one by default), None if the stream does not have it"""
        if stream is None:
            stream = self.__get_first_video_stream__()
        try:
            return stream[attr]
        except KeyError as e:
            log.logger.error("Video stream %s has no key %s\n", util.json_fmt(stream), e.args[0])
            return None

    def __get_stream_by_codec__(self, field: str, codec_list: tuple | list | str) -> dict | None:
        """Returns the first stream whose field (eg codec_type) is one of the values of the list, None if there is none"""
        log.logger.debug("Searching stream for codec %s = %s", field, codec_list)
        for stream in self.specs["streams"]:
            log.logger.debug("Found codec %s", stream[field])
            if stream[field] in codec_list:
                return stream
        return None

    def get_properties(self) -> dict:
        """Returns the properties of the file"""
        return self.get_file_properties()

    def __get_top_left__(self, width: int, height: int, **kwargs: object) -> tuple[int, int, str]:
        """Returns the top and left positions, and the name of the position, of a region of a given size in the media: from the top, left and position
        options, centered by default"""
        # The caller may give the dimensions of the frame (eg the displayed size of a rotated video)
        iw, ih = kwargs.get("dimensions") or self.dimensions(ignore_orientation=True)
        top: int | None = kwargs.get("top")
        left: int | None = kwargs.get("left")
        pos: str | None = kwargs.get("position")
        if top is None:
            if pos is None:
                pos = "center"
                top = (ih - height) // 2
            elif "top" in pos:
                top = 0
            elif "bottom" in pos:
                top = ih - height
            else:
                top = (ih - height) // 2
        if left is None:
            if pos is None:
                pos = "center"
                left = (iw - width) // 2
            elif "left" in pos:
                left = 0
            elif "right" in pos:
                left = iw - width
            else:
                left = (iw - width) // 2
        return (top, left, pos)

    def get_exif_data(self, force: bool = False) -> dict[str, str]:
        """Returns the EXIF data of the file as a dictionary. They are read only once, unless force is set"""
        if self._exif_data is None or force:
            with ExifToolHelper(executable=util.get_exiftool(), common_args=util.EXIFTOOL_ARGS, encoding="utf-8") as et:
                self._exif_data = et.get_metadata(self.filename)[0]
        return self._exif_data

    def set_exif_creation_date(self, some_datetime: datetime | str) -> None:
        """Sets the EXIF creation date of the file to a date"""
        if isinstance(some_datetime, datetime):
            time_to_set = datetime.strftime(some_datetime, EXIF_DATE_FMT)
        else:
            time_to_set = some_datetime
        with ExifToolHelper(executable=util.get_exiftool(), common_args=util.EXIFTOOL_ARGS, encoding="utf-8") as et:
            et.set_tags([self.filename], tags={"DateTimeOriginal": time_to_set}, params=["-P", "-overwrite_original"])

    def get_exif_creation_date(self) -> datetime | None:
        """Returns the EXIF creation date of the file (or the modification date of the file when there is none)"""
        exif_data = self.get_exif_data()
        if EXIF_ORIGINAL_DATE_TAG in exif_data:
            str_date = exif_data[EXIF_ORIGINAL_DATE_TAG]
        elif FILE_MODIFY_DATE_TAG in exif_data:
            str_date = exif_data[FILE_MODIFY_DATE_TAG]
        else:
            log.logger.warning("Can't find creation date in %s", util.json_fmt(exif_data))
            return None

        str_date: str | None = None
        creation_date: datetime | None = None
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

    def get_exif_device(self) -> str:
        """Returns the device (eg the camera) that generated the file, from its EXIF data"""
        exif_data = self.get_exif_data()
        device = ""
        for key in "EXIF:Make", "QuickTime:Author", "QuickTime:CompressorName":
            if key in exif_data:
                device = exif_data[key]
                break
        if "EXIF:Model" in exif_data:
            device += " " + exif_data["EXIF:Model"]
        return device

    def get_exif_dimensions(self) -> str:
        """Returns the dimensions of the media from its EXIF data, as WxH"""
        exif_data = self.get_exif_data()
        dimensions = ""
        for w_key, h_key in (
            ("File:ImageWidth", "File:ImageHeight"),
            ("EXIF:ExifImageWidth", "EXIF:ExifImageHeight"),
            ("QuickTime:SourceImageWidth", "QuickTime:SourceImageHeight"),
            ("QuickTime:ImageWidth", "QuickTime:ImageHeight"),
        ):
            if w_key in exif_data and h_key in exif_data:
                dimensions = f"{exif_data[w_key]}x{exif_data[h_key]}"
                break
        if not dimensions:
            dimensions = exif_data.get("Composite:ImageSize", "").replace(" ", "x")
        return dimensions

    def get_exif_gps_coordinates(self) -> tuple[float, float]:
        """Returns the latitude and the longitude of the media from its EXIF data"""
        lat: str | None = None
        long: str | None = None
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

    def set_exif_gps_coordinates(self, latitude: float, longitude: float) -> None:
        """Sets the GPS coordinates (latitude and longitude in degrees) in the EXIF data of the file"""
        lat_ref: str = "N"
        long_ref: str = "E"
        if latitude < 0:
            latitude = -latitude
            lat_ref = "S"
        if longitude < 0:
            longitude = -longitude
            long_ref = "W"
        with ExifToolHelper(executable=util.get_exiftool(), common_args=util.EXIFTOOL_ARGS, encoding="utf-8") as et:
            et.set_tags(
                [self.filename],
                tags={"EXIF:GPSLatitude": latitude, "EXIF:GPSLatitudeRef": lat_ref, "EXIF:GPSLongitude": longitude, "EXIF:GPSLongitudeRef": long_ref},
                params=["-P", "-overwrite_original"],
            )


# ---------------- Class methods ---------------------------------


def get_audio_filters(**kwargs: object) -> filters.Simple:
    """Returns the audio filters to apply according to the encoding options: volume, reverse"""
    log.logger.debug("Afilters options = %s", str(kwargs))
    afilters = filters.Simple(filters.AUDIO_TYPE)
    if kwargs.get("volume") is not None:
        vol = util.percent_or_absolute(kwargs["volume"])
        afilters.append(filters.volume(vol))
    if kwargs.get("audio_reverse", False) or kwargs.get("areverse", False):
        afilters.append(filters.areverse())
    log.logger.debug("afilters = %s", str(afilters))
    return afilters


def use_gpu_filters(**kwargs: object) -> bool:
    """True if the video is decoded and filtered by the GPU. The rotation and the flip are CPU filters only: with them only the encoding
    is done by the GPU (the frames are decoded and filtered on the CPU)"""
    return util.use_hardware_accel(**kwargs) and not kwargs.get("rotate") and not kwargs.get("flip")


def get_input_settings(**kwargs: object) -> list[str]:
    """Returns the ffmpeg options that apply to the input: start time, hardware accelerated decoding"""
    log.logger.debug("get_input_setting(%s)", str(kwargs))
    settings: list[str] = []
    if kwargs.get(opt.Option.START, "") != "":
        log.logger.debug("Adding start = %s", str(kwargs[opt.Option.START]))
        settings.append(opt.OPT_FMT.format(opt.OptionFfmpeg.START, kwargs[opt.Option.START]))
    if _must_encode_video(**kwargs) and use_gpu_filters(**kwargs):
        settings.append(util.HW_ACCEL_PREFIX)
    log.logger.debug("get_input_settings returns %s", str(settings))
    return settings


def get_prefilter_settings(**kwargs: object) -> list[str]:
    """Returns the ffmpeg options that apply before the filters (none)"""
    settings: list[str] = []
    return settings


def get_output_settings(file_type: str = fil.FileType.VIDEO_FILE, **kwargs: object) -> dict:
    """Returns the ffmpeg output options for the encoding options: codecs, resolution, bitrates, stop time, mute, fps"""
    settings: dict = {}
    log.logger.debug("get_output_setting(%s)", str(kwargs))

    if file_type == fil.FileType.VIDEO_FILE:
        settings[opt.Option.VCODEC] = _get_vcodec(**kwargs)

        if kwargs.get(opt.Option.RESOLUTION) is not None and not use_gpu_filters(**kwargs):
            settings[opt.OptionFfmpeg.RESOLUTION] = kwargs[opt.Option.RESOLUTION]

        if kwargs.get(opt.Option.VBITRATE) is not None:
            settings[opt.OptionFfmpeg.VBITRATE] = kwargs[opt.Option.VBITRATE]

    start: float = 0
    if kwargs.get(opt.Option.START) not in ("", None):
        start = util.to_seconds(kwargs[opt.Option.START])
    if kwargs.get(opt.Option.STOP) not in ("", None):
        settings[opt.OptionFfmpeg.STOP] = util.to_seconds(kwargs[opt.Option.STOP]) - start

    if kwargs.get(opt.Option.MUTE, False):
        settings[opt.OptionFfmpeg.MUTE] = True
    else:
        settings[opt.Option.ACODEC] = _get_acodec(**kwargs)
        if kwargs.get(opt.Option.ABITRATE) is not None:
            settings[opt.OptionFfmpeg.ABITRATE] = kwargs[opt.Option.ABITRATE]
        if kwargs.get(opt.Option.ACODEC) is not None:
            settings[opt.OptionFfmpeg.ACODEC] = kwargs[opt.Option.ACODEC]

    if kwargs.get(opt.Option.FPS) not in ("", None):
        settings[opt.OptionFfmpeg.FPS] = kwargs[opt.Option.FPS]

    log.logger.debug("get_output_settings returns %s", str(settings))
    return settings


def get_quality_settings(ffmpeg_codec: str, has_bitrate: bool = False, /, **kwargs: object) -> dict:
    """Returns the ffmpeg constant quality setting (-crf, or -cq for the hardware accelerated encoders) of the video quality
    (--quality high, medium or low, high by default), according to the ffmpeg video codec (ffmpeg_codec):
    h264: 18, 23 and 26 - h265: 23, 28 and 31.
    The quality is not applied (empty settings) when the video is copied, for the codecs without constant quality mode, and by default when
    a video bitrate is given (has_bitrate): a quality explicitly requested takes precedence over a bitrate"""
    quality = kwargs.get(opt.Option.QUALITY)
    if ffmpeg_codec == "copy" or (quality is None and has_bitrate):
        return {}
    quality = (quality or opt.DEFAULT_QUALITY).lower()
    if quality not in opt.QUALITY_LEVELS:
        raise ex.InputError(f"Invalid quality '{quality}', must be one of {', '.join(opt.QUALITY_LEVELS)}", "quality")
    if ffmpeg_codec in ("libx264", "h264_nvenc"):
        table = opt.CRF_H264
    elif ffmpeg_codec in ("libx265", "hevc_nvenc"):
        table = opt.CRF_H265
    else:
        if kwargs.get(opt.Option.QUALITY) is not None:
            log.logger.warning("The quality is not supported by the video codec %s, ignored", ffmpeg_codec)
        return {}
    return {(opt.OptionFfmpeg.CQ if ffmpeg_codec.endswith("_nvenc") else opt.OptionFfmpeg.CRF): table[quality]}


def _must_encode_video(**kwargs: object) -> bool:
    """Returns True if an option requires the video to be encoded, False if it can be copied"""
    for k, v in kwargs.items():
        if k == opt.Option.QUALITY and kwargs.get(opt.Option.VCODEC) != "copy":
            return True
        if k in (opt.Option.RESOLUTION, "speed", opt.Option.VBITRATE, "width", "height", "aspect", "reverse", "deshake", "rotate", "flip"):
            return True
        if k == opt.Option.VCODEC and v != "copy":
            return True
    return False


def _get_vcodec(**kwargs: object) -> str:
    """Returns the ffmpeg video codec to use: copy if the video must not be encoded, otherwise the requested or default one (the hardware accelerated
    one if requested)"""
    if _must_encode_video(**kwargs):
        vcodec = kwargs.get(opt.Option.VCODEC, conf.get_property("default.video.codec"))
        if util.use_hardware_accel(**kwargs):
            vcodec = opt.HW_ACCEL_CODECS[vcodec]
        else:
            vcodec = opt.CODECS[vcodec]
    else:
        vcodec = "copy"
    return vcodec


def _get_acodec(**kwargs: object) -> str:
    """Returns the audio codec to use: copy if the audio must not be encoded, otherwise the requested or default one"""
    acodec: str
    if not _must_encode_audio(**kwargs):
        acodec = "copy"
    else:
        acodec = kwargs.get(opt.Option.ACODEC, conf.get_property("default.audio.codec"))
    return acodec


def _must_encode_audio(**kwargs: object) -> bool:
    """Returns True if an option requires the audio to be encoded, False if it can be copied"""
    for k, v in kwargs.items():
        if k in (opt.Option.ABITRATE, "volume"):
            return True
        if k == opt.Option.ACODEC and v != "copy":
            return True
    return False


def build_target_file(source_file: str, profile: str | None) -> str:
    """Returns the name of the file generated from a source file with a profile: the name of the source with the profile as postfix and its extension
    Returns the name of the file generated from a source file with a profile: the name of the source with the profile as postfix and its extension"""
    extension = util.get_profile_extension(profile)
    if extension is None:
        extension = conf.get_property(f"default.{fil.get_type(source_file)}.format")
    if extension is None:
        extension = fil.extension(source_file)
    return util.add_postfix(source_file, profile, extension)


def get_crop_filter_options(width: int, height: int, top: int, left: int) -> str:
    """Returns the ffmpeg option that crops a video to a width and a height from a position"""
    # ffmpeg -i in.mp4 -filter:v "crop=out_w:out_h:x:y" out.mp4
    return f'-filter:v "crop={width}:{height}:{top}:{left}"'


def get_deshake_filter_options(width: int, height: int) -> str:
    """Returns the ffmpeg option that removes the shakiness of a video within a search range of width and height pixels"""
    # ffmpeg -i <in> -f mp4 -vf deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=16 -b:v 2048k <out>
    return f"-vf deshake=x=-1:y=-1:w=-1:h=-1:rx={width}:ry={height}"


def compute_fps(rate: str) -> str:
    """Simplifies the FPS calculation"""
    log.logger.debug("Calling compute_fps(%s)", rate)
    if re.match(r"^\d+\/\d+$", rate):
        a, b = [int(x) for x in rate.split("/")]
        return str(round(a / b, 1))
    return rate


def get_exif_creation_date(filename: str) -> datetime | None:
    """Returns the EXIF creation date of a file"""
    return MediaFile(filename).get_exif_creation_date()


def set_exif_creation_date(filename: str, some_datetime: datetime | str) -> None:
    """Sets the EXIF creation date of a file to a date"""
    MediaFile(filename).set_exif_creation_date(some_datetime)


def get_exif_gps_coordinates(filename: str) -> tuple[float, float]:
    """Returns the latitude and the longitude of a file from its EXIF data"""
    return MediaFile(filename).get_exif_gps_coordinates()


def set_exif_gps_coordinates(filename: str, latitude: float, longitude: float) -> None:
    """Sets the GPS coordinates (latitude and longitude in degrees) in the EXIF data of a file"""
    MediaFile(filename).set_exif_gps_coordinates(latitude, longitude)


def reduce_aspect_ratio(aspect_ratio: int | str, height: int | None = None) -> str:
    """Reduces the Aspect ratio calculation in prime factors"""
    if height is None:
        w, h = [int(x) for x in re.split("[:/x]", aspect_ratio)]
    else:
        w = aspect_ratio
        h = height
    for n in [2, 3, 5, 7, 11, 13, 17]:
        while w % n == 0 and h % n == 0:
            w = w // n
            h = h // n
    return f"{w}:{h}"


def concat(target_file: str, file_list: list[str]) -> None:
    """Concatenates audio and video files into a target file"""
    #  ffmpeg -i opening.mkv -i episode.mkv -i ending.mkv \
    #  -filter_complex "[0:v] [0:a] [1:v] [1:a] [2:v] [2:a] concat=n=3:v=1:a=1 [v] [a]" \
    #  -map "[v]" -map "[a]" output.mkv
    log.logger.info("Concatenating %s", str(file_list))
    cmd = filters.inputs_str(file_list)
    cmd = cmd + '-filter_complex "'
    for i in range(len(file_list)):
        cmd = cmd + f"[{i}:v] [{i}:a] "
    cmd = cmd + f'concat=n={len(file_list)}:v=1:a=1 [v] [a]" -map "[v]" -map "[a]" {target_file}'
    util.run_ffmpeg(cmd)


def strip_media_options(options: dict) -> dict:
    """Returns the options of a dictionary without the ones that are encoding options of the tool"""
    strip = {k: v for k, v in options.items() if k not in opt.M2F_MAPPING}
    log.logger.debug("stripped media options = %s", str(strip))
    return strip


def strip_ffmpeg_options(options: dict) -> dict:
    """Returns the options of a dictionary without the ones that are ffmpeg options"""
    strip = {k: v for k, v in options.items() if k not in opt.F2M_MAPPING}
    log.logger.debug("stripped ffmpeg options = %s", str(strip))
    return strip


def build_ffmpeg_options(options: dict, with_mapping: bool = False) -> str:
    """Returns the options of a dictionary as the options of an ffmpeg command line, optionally mapping the options of the tool to the ones of ffmpeg
    Returns the options of a dictionary as the options of an ffmpeg command line, optionally mapping the options of the tool to the ones of ffmpeg"""
    cmd = ""
    for k, v in options.items():
        if with_mapping:
            if k not in opt.M2F_MAPPING:
                log.logger.warning("Option %s can't be mapped to ffmpeg option", str(k))
                continue
            k = opt.M2F_MAPPING[k]
        if v is None or not v:
            continue
        if v is True:
            cmd = cmd + f" -{k}"
        else:
            cmd = cmd + f' -{k} "{v}"'
    log.logger.debug("Mapped ffmpeg options = %s", cmd)
    return cmd
