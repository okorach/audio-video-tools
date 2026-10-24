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

"""Video file tools"""

from __future__ import annotations
import datetime
import math
import os
from exiftool import ExifToolHelper
import re
from mediatools import log
import mediatools.exceptions as ex
import mediatools.resolution as res
import mediatools.utilities as util
import utilities.file as fil
import mediatools.mediafile as media
import mediatools.imagefile as image
import mediatools.options as opt
from filters import filter  # noqa: A004
from filters import filters
import mediatools.media_config as conf

H264_HW_DECODE_MAX_SIZE: int = 4096
H264_HW_DECODE_PIX_FMTS: tuple[str, ...] = ("yuv420p", "yuvj420p", "nv12")
DEFAULT_CROP_BOX: str = "1920x1080"
# Names accepted by --box (case insensitive) as aliases of a WxH size
CROP_BOX_ALIASES: dict[str, str] = {"4k": "3840x2160", "fhd": "1920x1080", "1k": "1920x1080", "hd": "1280x720"}


def parse_crop_box(box: str | None) -> tuple[str, str]:
    """Parses a crop box given as WxH or as an alias (4k, fhd, 1k, hd, case insensitive).
    Returns (width, height) as strings. Raises ValueError if the box is malformed"""
    value = str(box or DEFAULT_CROP_BOX).strip().lower()
    value = CROP_BOX_ALIASES.get(value, value)
    parts = value.split("x")
    if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
        raise ValueError(f"Invalid crop box '{box}', expected <width>x<height> or one of {', '.join(CROP_BOX_ALIASES)}")
    return parts[0].strip(), parts[1].strip()


FFMPEG_CLASSIC_FMT: str = '-i "{0}" {1} "{2}"'


class VideoFile(media.MediaFile):
    AV_PASSTHROUGH: str = f"-{opt.OptionFfmpeg.VCODEC} copy -{opt.OptionFfmpeg.ACODEC} copy -map 0 "

    """Video file abstraction"""

    def __init__(self, filename: str) -> None:
        if not fil.is_video_file(filename):
            raise ex.FileTypeError(file=filename, expected_type="video")

        self.aspect: str | None = None
        self.video_codec: str | None = None
        self.video_bitrate: int | None = None
        self.resolution: res.Resolution | None = None
        self.duration: float | None = None
        self.video_fps: float | None = None
        self.pixel_aspect: str | None = None
        self.audio_bitrate: int | None = None
        self.audio_codec: str | None = None
        self.audio_language: str | None = None
        self.audio_sample_rate: int | None = None
        self.year: int | None = None
        super().__init__(filename)
        self.get_specs()

    def get_specs(self) -> None:
        """Returns video file complete specs as dict"""
        # if self.specs is None:
        self.probe()
        self.decode_specs()

    def decode_specs(self) -> None:
        self.get_file_specs()
        self.get_video_specs()
        self.get_audio_specs()

    def get_video_specs(self) -> dict:
        """Returns video file video specs as dict"""
        stream = self.__get_first_video_stream__()
        _, _ = self.dimensions(stream)
        _ = self.get_fps(stream)
        _ = self.get_video_codec(stream)
        _ = self.get_pixel_aspect_ratio(stream)
        self.video_bitrate = int(stream.get("bit_rate", 0))
        if self.video_bitrate == 0:
            try:
                self.video_bitrate = self.specs["format"]["bit_rate"]
            except KeyError:
                log.logger.error("Can't find video_bitrate in %s", str(self.specs))
        self.duration = round(float(stream.get("duration", 0)), 3)
        if math.isclose(self.duration, 0.0):
            log.logger.error("Can't find duration in %s", str(stream))
        try:
            self.copyright = self.specs["format"]["tags"]["copyright"]
            log.logger.info("%s copyright = %s", self.filename, self.copyright)
        except KeyError:
            log.logger.info("%s has no copyright", self.filename)
        return self.specs

    def get_audio_specs(self) -> dict:
        """Returns video file audio specs as dict"""
        for stream in self.specs["streams"]:
            if stream["codec_type"] != "audio":
                continue
            self.audio_codec = self.__get_audio_stream_attribute__("codec_name", stream)
            self.audio_bitrate = self.__get_audio_stream_attribute__("bit_rate", stream)
            self.audio_sample_rate = self.__get_audio_stream_attribute__("sample_rate", stream)
            if "tags" in stream and "language" in stream["tags"]:
                self.audio_language = stream["tags"]["language"]
                if self.audio_bitrate is None:
                    self.audio_bitrate = stream["tags"]["BPS-eng"]
                if self.audio_language in util.LANGUAGE_MAPPING:
                    self.audio_language = util.LANGUAGE_MAPPING[self.audio_language]
            if self.audio_bitrate is not None:
                self.audio_bitrate = int(self.audio_bitrate)
            break
        return self.specs

    def get_aspect_ratio(self) -> str | None:
        """Returns video file aspect ratio"""
        if self.aspect is None:
            self.get_specs()
        return self.aspect

    def get_pixel_aspect_ratio(self, stream: dict | None = None) -> str | None:
        """Returns video file pixel aspect ratio"""
        if self.pixel_aspect is None:
            ar = stream.get("display_aspect_ratio", None)
            if ar is None:
                ar = f"{self.get_width()}:{self.get_height()}"
            self.aspect = media.reduce_aspect_ratio(ar)
            par = stream.get("sample_aspect_ratio", None)
            if par is None:
                par = media.reduce_aspect_ratio(f"{self.get_width()}:{self.get_height()}")
            self.pixel_aspect = media.reduce_aspect_ratio(par)
        return self.pixel_aspect

    def get_video_codec(self, stream: dict | None = None) -> str:
        """Returns video file video codec"""
        log.logger.debug("Getting video codec")
        if self.video_codec is not None:
            return self.video_codec
        if stream is None:
            stream = self.__get_first_video_stream__()
        self.video_codec = stream.get("codec_name", "")
        if self.video_codec == "":
            log.logger.error("Can't find video codec in stream %s\n", util.json_fmt(stream))
        return self.video_codec

    def get_video_duration(self) -> float | None:
        if self.duration is None:
            self.duration = round(float(self.__get_video_stream_attribute__("duration")), 3)
        return self.duration

    def get_audio_codec(self) -> str | None:
        """Returns video file audio codec"""
        if self.audio_codec is None:
            self.get_specs()
        return self.audio_codec

    def get_audio_bitrate(self) -> int | None:
        """Returns video file audio bitrate"""
        if self.audio_bitrate is None:
            self.get_specs()
        return self.audio_bitrate

    def get_duration(self) -> float | None:
        """Returns video file duration"""
        if self.duration is None:
            self.get_specs()
        return self.duration

    def can_hw_decode(self) -> bool:
        """Returns False if the video can't be decoded by the GPU (NVDEC), in which case ffmpeg decodes it on the CPU:
        H.264 is limited to 4096 pixels in each dimension and to 8 bits 4:2:0"""
        stream = self.__get_first_video_stream__()
        if stream.get("codec_name") != "h264":
            return True
        too_big = max(int(stream.get("width", 0)), int(stream.get("height", 0))) > H264_HW_DECODE_MAX_SIZE
        return not too_big and stream.get("pix_fmt", "yuv420p") in H264_HW_DECODE_PIX_FMTS

    def get_fps(self, stream: dict | None = None) -> float | None:
        if self.video_fps is None:
            if stream is None:
                stream = self.__get_first_video_stream__()
                log.logger.debug("Video stream is %s", util.json_fmt(stream))
            for tag in ["avg_frame_rate", "r_frame_rate"]:
                if tag in stream:
                    self.video_fps = media.compute_fps(stream[tag])
                    break
        return self.video_fps

    def dimensions(self, stream: dict | None = None, ignore_orientation: bool = True) -> tuple[int, int]:
        log.logger.debug("Getting video dimensions")
        if self.resolution is None:
            if stream is None:
                stream = self.__get_first_video_stream__()
            w = int(util.get_first_value(stream, ("width", "codec_width", "coded_width")))
            h = int(util.get_first_value(stream, ("height", "codec_height", "coded_height")))
            self.resolution = res.Resolution(width=w, height=h)
        log.logger.debug("Resolution = %s", str(self.resolution))
        return (self.resolution.width, self.resolution.height)

    def __main_video_stream_position__(self) -> int:
        """Returns the position of the main video stream among the video streams (ffmpeg v:<n> specifier)"""
        main = self.__get_first_video_stream__()
        position = 0
        for stream in self.specs["streams"]:
            if stream is main:
                break
            if stream["codec_type"] == "video":
                position += 1
        return position

    def get_rotation(self) -> int:
        """Returns the rotation (degrees, 0 if none) that players and ffmpeg apply to the first video stream when displaying it"""
        stream = self.__get_first_video_stream__() or {}
        for side_data in stream.get("side_data_list", []):
            if "rotation" in side_data:
                return int(float(side_data["rotation"]))
        try:
            return int(float(stream.get("tags", {}).get("rotate", 0)))
        except (TypeError, ValueError):
            return 0

    def displayed_dimensions(self) -> tuple[int, int]:
        """Returns the dimensions of the video once rotation is applied (width and height swapped for a 90 or 270 degrees rotation)"""
        w, h = self.dimensions()
        return (h, w) if abs(self.get_rotation()) % 180 == 90 else (w, h)

    def get_height(self) -> int:
        if self.resolution is None:
            _, _ = self.dimensions()
        return self.resolution.height

    def get_width(self) -> int:
        if self.resolution is None:
            _, _ = self.dimensions()
        return self.resolution.width

    def get_resolution(self) -> res.Resolution | None:
        if self.resolution is None:
            _, _ = self.dimensions()
        return self.resolution

    def calc_resolution(self, w: int | str, h: int | str) -> tuple[int, int]:
        return self.resolution.calc_resolution(w, h)

    def get_audio_properties(self) -> dict:
        if self.audio_codec is None:
            self.get_specs()
        return {
            opt.Option.ABITRATE: self.audio_bitrate,
            opt.Option.ACODEC: self.audio_codec,
            "audio_language": self.audio_language,
            "audio_sample_rate": self.audio_sample_rate,
        }

    def get_video_properties(self) -> dict:
        if self.video_codec is None:
            self.get_specs()
        return {
            "file_size": self.size(),
            opt.Option.FORMAT: self.format,
            opt.Option.VBITRATE: self.video_bitrate,
            opt.Option.VCODEC: self.video_codec,
            opt.Option.FPS: self.video_fps,
            "width": self.get_width(),
            "height": self.get_height(),
            opt.Option.ASPECT: self.aspect,
            "pixel_aspect_ratio": self.pixel_aspect,
            "author": self.author,
            "copyright": self.copyright,
            "year": self.year,
        }

    def get_properties(self) -> dict:
        audio_props = self.get_audio_properties()  # Loads the specs of the file: before the file properties are read
        video_props = self.get_video_properties()
        all_props = self.get_file_properties()
        all_props.update(audio_props)
        all_props.update(video_props)
        all_props["resolution"] = str(all_props["resolution"])
        log.logger.debug("Properties(%s) = %s", self.filename, str(all_props))
        return all_props

    @util.hw_accel_fallback
    def crop(self, out_file: str | None = None, **kwargs) -> str:
        """Crops a region of the video.
        The region size is given by either box="WxH" (default 1920x1080) or width and height.
        The region location is given by position (any combination of top, center, bottom, left, right).
        The output video has the same codec and container as the input, a video bitrate proportional to
        the cropped surface, and audio (and other) tracks unchanged.
        Raises ValueError if the crop region is bigger than the source video"""
        width, height = kwargs.get("width"), kwargs.get("height")
        if width is None or height is None:
            width, height = parse_crop_box(kwargs.get("box"))
        width, height = self.calc_resolution(width, height)
        # ffmpeg applies the rotation of the video before filtering, so the crop is relative to the displayed size
        src_w, src_h = self.displayed_dimensions()
        if width > src_w or height > src_h:
            msg = f"Crop box {width}x{height} is bigger than source video {src_w}x{src_h}"
            log.logger.error(msg)
            raise ValueError(msg)
        top, left, pos = self.__get_top_left__(width=width, height=height, position=kwargs.get("position"), dimensions=(src_w, src_h))

        self.get_specs()
        codec = self.get_video_codec()
        hw_accel = util.use_hardware_accel(**kwargs)
        if hw_accel:
            # ffprobe reports hevc, the option mapping knows it as h265
            codec = opt.HW_ACCEL_CODECS.get("h265" if codec == "hevc" else codec, codec)
        # Only the main video stream is filtered and re-encoded (v:<n>), the other video streams (eg thumbnails),
        # the audio and subtitle streams are copied. Data streams (eg camera telemetry) are dropped, because the
        # container can't always hold them (ffmpeg fails with "codec none not supported in container")
        n = self.__main_video_stream_position__()
        options = [f'-map 0:v? -map 0:a? -map 0:s? -c copy -c:v:{n} "{codec}"']
        if self.video_bitrate:
            # Target bitrate proportional to the proportion of the source video that is kept
            options.append(f"-b:v:{n} {int(self.video_bitrate * width * height / (src_w * src_h))}")
        else:
            log.logger.warning("Can't find video bitrate of %s, using encoder default", self.filename)

        ext = fil.extension(self.filename)
        out_file = util.automatic_output_file_name(out_file, self.filename, "crop", ext)
        # Decode on GPU but keep frames in system memory since the crop filter is a CPU one
        hw_prefix = "-hwaccel cuda " if hw_accel else ""
        cmd = f'{hw_prefix}-i "{self.filename}" -filter:v:{n} "{filters.crop(width, height, left, top)}" {" ".join(options)} "{out_file}"'
        creation_date = get_creation_date(self.filename)
        util.run_ffmpeg(cmd, self.duration)
        # The cropped video keeps the creation date of the source
        if os.path.isfile(out_file):
            set_creation_date(out_file, creation_date)
        return out_file

    def add_metadata(self, **metadatas) -> str:
        # ffmpeg -i in.mp4 -vcodec copy -c:a copy -map 0 -metadata year=<year>
        # -metadata copyright="(c) O. Korach <year>"  -metadata author="Olivier Korach"
        # -metadata:s:a:0 language=fre -metadata:s:a:0 title="Avec musique"
        # -metadata:s:v:0 language=fre -disposition:a:0 default -disposition:a:1 none "%~1.meta.mp4"
        log.logger.debug("Add metadata: %s", str(metadatas))

        options = [filters.vcodec("copy"), filters.acodec("copy")]

        # Handle copyright, author, year
        for key, value in metadatas.items():
            if key in ("author", "year"):
                options.append(filters.metadata(key, value))
            if key == "copyright":
                options.append(filters.metadata(key, f"© {value}"))

        nb_tracks = self.__get_number_of_audio_tracks()
        # Handle default_track
        if "default_track" in metadatas:
            options.append(filters.disposition(metadatas["default_track"], nb_tracks))

        if "language" in metadatas:
            for m in metadatas["language"]:
                try:
                    track, value, details = m.split(":", maxsplit=3)
                    options.append(filters.metadata("language", value, track))
                    options.append(filters.metadata("title", details, track))
                except ValueError:
                    track, value = m.split(":", maxsplit=2)
                    options.append(filters.metadata("language", value, track))

        output_file = util.add_postfix(self.filename, "meta")
        util.run_ffmpeg(f'-i "{self.filename}" -map 0 {filters.format_options(options)} "{output_file}"', self.duration)
        return output_file

    def add_stream_property(self, stream_index: int | str, prop: str, value: str | None = None) -> str:
        direct_copy = "-vcodec copy -c:a copy -map 0"
        output_file = util.add_postfix(self.filename, "meta")
        if value is None:
            stream_index, value = stream_index.split(":")
        util.run_ffmpeg(f'-i "{self.filename}" {direct_copy} -metadata:s:a:{stream_index} {prop}="{value}" "{output_file}"', self.duration)
        return output_file

    def add_stream_language(self, stream_index: int | str, language: str | None = None) -> str:
        return self.add_stream_property(stream_index, "language", language)

    def add_stream_title(self, stream_index: int | str, title: str | None = None) -> str:
        return self.add_stream_property(stream_index, "title", title)

    def add_author(self, author: str) -> str:
        return self.add_metadata(author=author)

    def add_year(self, year: int | str) -> str:
        return self.add_metadata(year=year)

    def add_audio_tracks(self, *audio_files: str, out_file: str | None = None) -> str:
        maps = " ".join([f"-map {i}" for i in range(len(audio_files) + 1)])
        inputs = " ".join([f'-i "{file}"' for file in [self.filename, *audio_files]])
        out_file = util.automatic_output_file_name(outfile=out_file, infile=self.filename, postfix="muxed")
        util.run_ffmpeg(f'{inputs} {maps} -dn -codec copy "{out_file}"', self.duration)
        return out_file

    def set_author(self, author: str) -> None:
        self.author = author

    def get_author(self) -> str | None:
        return self.author

    def set_copyright(self, copyr: str) -> None:
        self.copyright = copyr

    def get_copyright(self) -> str | None:
        return self.copyright

    @util.hw_accel_fallback
    def encode(self, target_file: str | None = None, profile: str | None = None, **kwargs) -> str:
        """Encodes a file
        - target_file is the name of the output file. Optional
        - Profile is the encoding profile as per the VideoTools.properties config file
        - **kwargs accepts at large panel of other optional options"""
        kwargs = util.get_all_options(**kwargs)
        log.logger.debug("Encoding %s with profile %s and args %s", self.filename, profile, str(kwargs))
        if target_file is None:
            target_file = media.build_target_file(self.filename, profile)

        input_settings = media.get_input_settings(**kwargs)
        if util.HW_ACCEL_PREFIX in input_settings and not self.can_hw_decode():
            log.logger.info("%s can't be decoded by the GPU, decoding it on the CPU", self.filename)
            input_settings.remove(util.HW_ACCEL_PREFIX)
        prefilter_settings = media.get_prefilter_settings(**kwargs)
        raw_settings = util.get_profile_params(profile)
        if raw_settings.pop(opt.OptionFfmpeg.DEINTERLACE, False):
            # -deinterlace is not supported by recent ffmpeg versions, the yadif filter does the same
            kwargs[opt.Option.DEINTERLACE] = True
        video_filters = self.__get_video_filters(**kwargs)
        audio_filters = media.get_audio_filters(**kwargs)
        output_settings = media.get_output_settings(**kwargs)
        ext = target_file.split(".")[-1].lower()
        log.logger.debug("Output file extension = %s", ext)
        if ext == "mp3" and output_settings[opt.OptionFfmpeg.ACODEC] != "copy":
            output_settings[opt.OptionFfmpeg.ACODEC] = "libmp3lame"
            log.logger.info("Patching codec for MP3 audio output")
        elif ext in ("m3a", "aac") and output_settings[opt.OptionFfmpeg.ACODEC] != "copy":
            output_settings[opt.OptionFfmpeg.ACODEC] = "aac"
            log.logger.info("Patching codec for AAC audio output")

        output_str = media.build_ffmpeg_options({**raw_settings, **output_settings})

        # Preserve all audio and subtitle streams unless audio is explicitly muted (-an)
        if kwargs.get(opt.Option.MUTE, False):
            mapping = "-map 0:v:0"
        else:
            mapping = "-map 0:v:0 -map 0:a? -map 0:s? -c:s copy"

        cmd = f'{" ".join(input_settings)} -i "{self.filename}" {" ".join(prefilter_settings)}'
        cmd += f'{video_filters!s} {audio_filters!s} {output_str} {mapping} "{target_file}"'
        eta_duration = kwargs.get("batch_remaining", self.duration)
        speed_val = kwargs.get("speed", None)
        if speed_val is not None:
            try:
                speed_factor = float(util.percent_or_absolute(str(speed_val)))
                if speed_factor > 0:
                    eta_duration = eta_duration / speed_factor
            except ValueError:
                pass
        util.run_ffmpeg(cmd, eta_duration)
        log.logger.info("File %s encoded", target_file)
        return target_file

    def set_creation_date(self, some_datetime: datetime.datetime | str) -> None:
        if isinstance(some_datetime, datetime.datetime):
            time_to_set = some_datetime.strftime(media.EXIF_DATE_FMT)
        else:
            time_to_set = some_datetime
        p = ["-P", "-overwrite_original"]
        with ExifToolHelper(executable=util.get_exiftool(), encoding="utf-8") as et:
            et.set_tags([self.filename], tags={"CreateDate": time_to_set, "ModifyDate": time_to_set, "DateTimeOriginal": time_to_set}, params=p)
            et.set_tags(
                [self.filename], tags={"EXIF:CreateDate": time_to_set, "EXIF:ModifyDate": time_to_set, "EXIF:DateTimeOriginal": time_to_set}, params=p
            )
            et.set_tags(
                [self.filename],
                tags={
                    "Composite:SubSecCreateDate": time_to_set,
                    "Composite:SubSecDateTimeOriginal": time_to_set,
                    "Composite:SubSecModifyDate": time_to_set,
                    "Quicktime:CreateDate": time_to_set,
                    "Quicktime:DateTimeOriginal": time_to_set,
                    "QuickTime:MediaCreateDate": time_to_set,
                    "QuickTime:MediaModifyDate": time_to_set,
                    "QuickTime:TrackCreateDate": time_to_set,
                    "QuickTime:TrackModifyDate": time_to_set,
                    "QuickTime:CreateDate": time_to_set,
                    "QuickTime:ModifyDate": time_to_set,
                },
                params=p,
            )

    def get_exif_bitrate(self) -> int | None:
        exif_data = self.get_exif_data()
        bitrate = None
        if "Composite:AvgBitrate" in exif_data:
            bitrate = round(int(exif_data["Composite:AvgBitrate"]) / 1024 / 1024)
        return bitrate

    def get_exif_codec(self) -> str:
        exif_data = self.get_exif_data()
        codec = ""
        if "QuickTime:CompressorID" in exif_data:
            codec = exif_data["QuickTime:CompressorID"]
        if codec == "avc1":
            codec = "h264"
        elif codec == "hev1":
            codec = "h265"
        return codec

    def get_exif_fps(self) -> float | None:
        exif_data = self.get_exif_data()
        fps = None
        if "QuickTime:VideoFrameRate" in exif_data:
            fps = round(float(exif_data["QuickTime:VideoFrameRate"]))
        return fps

    # ----------------- Private methods ------------------------------------------

    def __get_number_of_audio_tracks(self) -> int:
        n = 0
        for stream in self.specs["streams"]:
            if stream["codec_type"] != "audio":
                n += 1
        return n

    @staticmethod
    def __get_fade_duration(fade: object) -> float:
        """The fade in / fade out duration (--fade) in seconds, 0.5 if it's not a number"""
        try:
            return float(fade)
        except (TypeError, ValueError):
            return 0.5

    def __get_encoded_duration(self, **kwargs) -> float:
        """The duration of the part of the video that is encoded (the whole video, or between start and stop)"""
        start = util.to_seconds(kwargs[opt.Option.START]) if kwargs.get(opt.Option.START) not in ("", None) else 0.0
        stop = util.to_seconds(kwargs[opt.Option.STOP]) if kwargs.get(opt.Option.STOP) not in ("", None) else self.get_duration()
        return stop - start

    def __get_scale_filter(self, **kwargs) -> str | None:
        """Returns the scale filter for the requested --width, --height or --resolution, None if the video is not resized.
        The unspecified dimension is computed to keep the aspect ratio (-2 keeps it even, as required by most encoders)"""
        width, height = kwargs.get(opt.Option.WIDTH), kwargs.get(opt.Option.HEIGHT)
        if not width and not height:
            return None
        width = width if width and width > 0 else -2
        height = height if height and height > 0 else -2
        if util.use_hardware_accel(**kwargs):
            # The frames of a video that the GPU can't decode are in system memory, they must be uploaded to the GPU
            upload = "" if self.can_hw_decode() else "hwupload_cuda,"
            return f"{upload}scale_cuda={width}:{height}"
        if kwargs.get(opt.Option.RESOLUTION) is not None:
            # Software resize with a --resolution is done by the -s output option
            return None
        return f"scale={width}:{height}"

    def __get_video_filters(self, **kwargs) -> filter.Simple:
        log.logger.debug("Vfilters options = %s", str(kwargs))
        vfilters = filter.Simple(filters.VIDEO_TYPE)
        if kwargs.get(opt.Option.DEINTERLACE, False):
            vfilters.append("yadif")
        if kwargs.get("speed") is not None:
            vfilters.append(filter.speed(kwargs["speed"]))
        if kwargs.get("reverse", False):
            vfilters.append(filter.Reverse())
        if "deshake" in kwargs:
            rx, ry = [int(x) for x in kwargs["deshake"].split("x")]
            vfilters.append(filter.deshake(rx=rx, ry=ry))
            if not kwargs.get("no_crop", False):
                w, h = self.dimensions()
                vfilters.append(filter.crop(w - rx, h - ry, rx // 2, ry // 2))
        if kwargs.get("vidstab_trf") is not None:
            trf = kwargs["vidstab_trf"]
            vfilters.append(f"vidstabtransform=input='{trf}',unsharp=5:5:0.8:3:3:0.4")
        if kwargs.get("fade", False):
            fade_duration = self.__get_fade_duration(kwargs["fade"])
            vfilters.append(filter.FadeIn(duration=fade_duration))
            vfilters.append(filter.FadeOut(start=max(self.__get_encoded_duration(**kwargs) - fade_duration, 0.0), duration=fade_duration))
        scale = self.__get_scale_filter(**kwargs)
        if scale:
            vfilters.append(scale)
        if kwargs.get("color_eq") is not None:
            if util.use_hardware_accel(**kwargs):
                log.logger.warning("Skipping eq color filter: not compatible with GPU hw acceleration (use --software_filters to enable)")
            else:
                vfilters.append(kwargs["color_eq"])
        log.logger.debug("vfilters = %s", str(vfilters))
        return vfilters


def get_size_option(cmdline: str) -> str:
    m = re.search(r"-s\s+(\S+)", cmdline)
    return m.group(1) if m else ""


def get_video_codec_option(cmdline: str) -> str:
    m = re.search(r"-vcodec\s+(\S+)", cmdline)
    if m:
        return m.group(1)
    m = re.search(r"-c:v\s+(\S+)", cmdline)
    return m.group(1) if m else ""


def get_audio_codec_option(cmdline: str) -> str:
    m = re.search(r"-acodec\s+(\S+)", cmdline)
    if m:
        return m.group(1)
    m = re.search(r"-c:a\s+(\S+)", cmdline)
    return m.group(1) if m else ""


def get_format_option(cmdline: str) -> str:
    m = re.search(r"-f\s+(\S+)", cmdline)
    return m.group(1) if m else ""


def get_audio_bitrate_option(cmdline: str) -> str:
    m = re.search(r"-ab\s+(\S+)", cmdline)
    if m:
        return m.group(1)
    m = re.search(r"-b:a\s+(\S+)", cmdline)
    return m.group(1) if m else ""


def get_video_bitrate_option(cmdline: str) -> str:
    m = re.search(r"-vb\s+(\S+)", cmdline)
    if m:
        return m.group(1)
    m = re.search(r"-b:v\s+(\S+)", cmdline)
    return m.group(1) if m else ""


def get_aspect_ratio_option(cmdline: str) -> str:
    m = re.search(r"-aspect\s+(\S+)", cmdline)
    return m.group(1) if m else ""


def get_frame_rate_option(cmdline: str) -> str:
    m = re.search(r"-r\s+(\S+)", cmdline)
    return m.group(1) if m else ""


def get_crop_filter_options(width: int, height: int, top: int, left: int) -> str:
    # ffmpeg -i in.mp4 -filter:v "crop=out_w:out_h:x:y" out.mp4
    return f"-filter:v crop={width}:{height}:{top}:{left}"


@util.hw_accel_fallback
def concat(target_file: str, file_list: list[str], with_audio: bool = True, hw_accel: bool | str = "auto") -> str:
    """Concatenates several video files - They must have same video+audio format and bitrate
    hw_accel is the hardware acceleration mode: auto, on or off"""
    file_list = sorted(file_list, key=lambda f: os.path.basename(f).lower())
    log.logger.info("%s = %s", target_file, " + ".join(file_list))

    first = VideoFile(file_list[0])
    n_audio = sum(1 for s in first.specs["streams"] if s["codec_type"] == "audio") if with_audio else 0
    n_files = len(file_list)
    total_duration = (first.duration or 0.0) + sum(VideoFile(f).duration or 0.0 for f in file_list[1:])

    # Input stream references: [i:v] [i:a:0] [i:a:1] ... for each file
    cmplx = "".join(f"[{i}:v]" + "".join(f"[{i}:a:{j}]" for j in range(n_audio)) for i in range(n_files))
    # Output labels: [outv] [outa0] [outa1] ...
    audio_out_labels = "".join(f"[outa{j}]" for j in range(n_audio))
    cmplx += f"concat=n={n_files}:v=1:a={n_audio}[outv]{audio_out_labels}"

    mapping = '-map "[outv]"' + "".join(f' -map "[outa{j}]"' for j in range(n_audio))

    if util.use_hardware_accel(hw_accel=hw_accel):
        # Decode each input on the GPU; concat filter runs on CPU frames
        files_str = " ".join(f'-hwaccel cuda -i "{f}"' for f in file_list)
        out_codec = opt.HW_ACCEL_CODECS.get(first.video_codec or "", "hevc_nvenc")
        log.logger.info("Using GPU acceleration: decode=cuda, encode=%s", out_codec)
    else:
        files_str = filters.inputs_str(file_list)
        out_codec = "libx265"

    cmd = f'{files_str} -filter_complex "{cmplx}" {mapping} -s "{first.resolution!s}"'
    cmd += f' -vcodec "{out_codec}" -b:v "{first.video_bitrate!s}" "{target_file}"'
    util.run_ffmpeg(cmd.strip(), total_duration)
    return target_file


def add_video_args(parser) -> object:
    """Parses options specific to video encoding scripts"""
    parser.add_argument("-p", "--profile", required=False, help="Profile to use for encoding")

    parser.add_argument("--" + opt.Option.VCODEC, required=False, help="Video codec (h264, h265, mpeg2, xvid...)")
    parser.add_argument("--" + opt.Option.ACODEC, required=False, help="Audio codec (mp3, aac, ac3...)")

    parser.add_argument("--" + opt.Option.VBITRATE, required=False, help="Video bitrate eg 1024k")
    parser.add_argument("--" + opt.Option.ABITRATE, required=False, help="Audio bitrate eg 128k")

    parser.add_argument("--fade", required=False, help="Fade in/out duration")

    parser.add_argument("-t", "--timeranges", required=False, help="Ranges of encoding <start>:<end>,<start>:<end>")

    parser.add_argument("-f", "--" + opt.Option.FORMAT, required=False, help="Output file format eg mp4")
    parser.add_argument("-r", "--" + opt.Option.FPS, required=False, help="Video framerate of the output eg 25")

    parser.add_argument("--asampling", required=False, help="Audio sampling eg 44100")
    parser.add_argument("--" + opt.Option.ACHANNEL, required=False, help="Audio channel to pick")
    parser.add_argument(
        "--" + opt.Option.DEINTERLACE, required=False, default=False, dest=opt.Option.DEINTERLACE, action="store_true", help="Deinterlace video"
    )

    return parser


def __get_aspect_ratio__(width: int, height: int, **kwargs) -> str:
    if kwargs.get("aspect") is None:
        aw, ah = re.split(":", media.reduce_aspect_ratio(width, height))
    else:
        aw, ah = re.split(":", kwargs["aspect"])
    return f"{aw}:{ah}"


def __get_audio_channel_mapping__(**kwargs) -> str:
    # Hack for channels selection
    if opt.Option.ACHANNEL not in kwargs:
        return ""
    mapping = "-map 0:v:0"
    mapping += " ".join([f"-map 0:a:{x}" for x in str(kwargs[opt.Option.ACHANNEL]).split(",")])
    return mapping


def __build_slideshow__(input_files: list[str], outfile: str = "slideshow.mp4", resolution: str | None = None, **kwargs) -> str:
    log.logger.debug("%s = slideshow(%s)", outfile, " + ".join(input_files))
    # The filters of the slideshow run on the CPU, only the encoding is done by the GPU (decoding some of the clips on the GPU
    # and the others on the CPU fails). If it fails anyway, slideshow() runs it again on the CPU
    hw_accel = util.use_hardware_accel(**kwargs)

    transition_duration = float(conf.get_property("default.fade.duration"))
    fcomp = filters.Complex(*[VideoFile(f) for f in input_files])

    # Consecutive clips are cross-faded pairwise with xfade (clip-to-clip, no alpha compositing involved), then the
    # whole result gets a plain fade in/out at its very start/end. A hand-rolled alpha-fade/overlay chain was tried
    # first but ffmpeg's overlay filter only honors the alpha of its 2nd (top) input, so chaining clips as each
    # other's background silently dropped the fade in of the first clip and the fade out of the last one as soon as
    # more than 3 clips were chained
    total_duration = fcomp.inputs[0].duration
    last_out = "0:v"
    for i in range(1, len(fcomp.inputs)):
        xfade_offset = total_duration - transition_duration
        last_out = fcomp.add_filtergraph([last_out, f"{i}:v"], f"xfade=transition=fade:duration={transition_duration}:offset={xfade_offset}")
        total_duration += fcomp.inputs[i].duration - transition_duration

    fade_in = filter.fade_in(duration=transition_duration, alpha=0)
    fade_out = filter.fade_out(start=total_duration - transition_duration, duration=transition_duration, alpha=0)
    last_out = fcomp.add_filtergraph(last_out, f"{fade_in},{fade_out}")
    last_out = fcomp.add_filtergraph(last_out, filters.setsar("1:1"))

    encoder = "-c:v h264_nvenc -cq 18" if hw_accel else "-crf 18 -preset slow"
    util.run_ffmpeg(
        f'{fcomp.format_inputs()} {fcomp!s} {encoder} -s "{resolution}" -map "[{last_out}]" "{outfile}"',
        total_duration,
    )

    return outfile


@util.hw_accel_fallback
def slideshow(*inputs: str, outfile: str | None = None, resolution: str | None = None, hw_accel: bool | str = "auto") -> tuple[str, list]:
    """Builds a high quality video slide show from a set of photos: each photo is converted to a short video
    with a slow zoom or panorama effect, slides are cross-faded into each other, and the output fades in/out at the
    start/end. outfile defaults to the basename of the first input photo with the video extension.
    Returns the (output file, list of per-photo operations) tuple"""
    log.logger.info("slideshow(%s)", str(inputs))
    MAX_SLIDESHOW_AT_ONCE = 30
    slideshow_files = fil.file_list(*inputs)
    video_files: list[str] = []
    all_video_files: list[list[str]] = []
    slideshows: list[str] = []
    operations: list = []
    if resolution is None:
        resolution = conf.get_property(conf.SLIDESHOW_RESOLUTION_KEY)
    fmt = conf.get_property("default.video.format")
    outfile = outfile or f"{fil.strip_extension(slideshow_files[0])}.{fmt}"
    log.logger.info("Final slideshow file will be %s", outfile)

    for slide_file in slideshow_files:
        if fil.is_image_file(slide_file):
            try:
                out_file, details = image.ImageFile(slide_file).to_video(with_effect=True, resolution=resolution, hw_accel=hw_accel)
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
            slideshows.append(
                __build_slideshow__(
                    video_files,
                    resolution=resolution,
                    outfile=f"{fil.strip_extension(outfile)}.part{len(slideshows)}.{os.getpid()}.{fmt}",
                    hw_accel=hw_accel,
                )
            )
            all_video_files.append(video_files)
            video_files = []
    if len(all_video_files) == 0:
        return (__build_slideshow__(video_files, resolution=resolution, outfile=outfile, hw_accel=hw_accel), operations)
    slideshows.append(
        __build_slideshow__(
            video_files,
            resolution=resolution,
            outfile=f"{fil.strip_extension(outfile)}.part{len(slideshows)}.{os.getpid()}.{fmt}",
            hw_accel=hw_accel,
        )
    )
    return (concat(target_file=outfile, file_list=slideshows, with_audio=False, hw_accel=hw_accel), operations)


def speed(filename: str, target_speed: str | float, output: str | None = None, mute: bool = True, **kwargs) -> str:
    """Changes the speed of a video. The size is unchanged and the video bitrate is the one of the source, unless a profile or a bitrate is given"""
    speed_str = str(target_speed)
    if not speed_str.endswith(("x", "%")):
        speed_str += "x"
    output = util.automatic_output_file_name(outfile=output, infile=filename, postfix=speed_str)
    vf = VideoFile(filename)
    if vf.video_bitrate and kwargs.get("vbitrate") is None and kwargs.get("profile") is None:
        kwargs["vbitrate"] = vf.video_bitrate
    return vf.encode(speed=target_speed, target_file=output, mute=mute, **kwargs)


def volume(filename: str, vol: str | float, output: str | None = None, **kwargs) -> str:
    output = util.automatic_output_file_name(outfile=output, infile=filename, postfix="volume")
    return VideoFile(filename).encode(volume=vol, target_file=output, **kwargs)


def reverse(filename: str, output: str | None = None, mute: bool = True, **kwargs) -> str:
    kwargs["hw_accel"] = False  # Reverse filter not compatible with HW accel
    output = util.automatic_output_file_name(outfile=output, infile=filename, postfix="reverse")
    return VideoFile(filename).encode(reverse=True, target_file=output, mute=mute, **kwargs)


def color_enhance(
    filename: str, output: str | None = None, *, saturation: float = 1.3, contrast: float = 1.1, brightness: float = 0.0, gamma: float = 1.0, **kwargs
) -> str:
    """Enhances video colors using the ffmpeg eq filter (saturation, contrast, brightness, gamma)."""
    eq = f"eq=saturation={saturation}:contrast={contrast}:brightness={brightness}:gamma={gamma}"
    log.logger.info("Color enhancing %s: %s", filename, eq)
    output = util.automatic_output_file_name(outfile=output, infile=filename, postfix="color")
    vf = VideoFile(filename)
    if vf.video_bitrate and "vbitrate" not in kwargs:
        kwargs["vbitrate"] = vf.video_bitrate
    return vf.encode(target_file=output, color_eq=eq, **kwargs)


def deshake(filename: str, output: str | None = None, **kwargs) -> str:
    output = util.automatic_output_file_name(infile=filename, outfile=output, postfix="deshake")
    return VideoFile(filename).encode(target_file=output, **kwargs)


def set_creation_date(filename: str, new_date: datetime.datetime | None) -> bool:
    if new_date is None:
        return False
    exif_date = datetime.datetime.strftime(new_date, util.EXIF_DATE_FMT)
    log.logger.info("Setting creation date of %s to %s", filename, exif_date)
    p = ["-P", "-overwrite_original"]
    try:
        with ExifToolHelper(executable=util.get_exiftool(), encoding="utf-8") as et:
            et.set_tags([filename], tags={"File:FileCreateDate": exif_date, "File:FileModifyDate": exif_date}, params=p)
            if fil.is_image_file(filename):
                et.set_tags([filename], tags={"DateTimeOriginal": exif_date}, params=p)
            elif fil.is_video_file(filename):
                log.logger.info("Tagging video file")
                et.set_tags([filename], tags={"CreateDate": exif_date, "ModifyDate": exif_date, "DateTimeOriginal": exif_date}, params=p)
                et.set_tags(
                    [filename],
                    tags={
                        "EXIF:CreateDate": exif_date,
                        "EXIF:ModifyDate": exif_date,
                        "EXIF:DateTimeOriginal": exif_date,
                    },
                    params=p,
                )
                et.set_tags(
                    [filename],
                    tags={
                        "Composite:SubSecCreateDate": exif_date,
                        "Composite:SubSecDateTimeOriginal": exif_date,
                        "Composite:SubSecModifyDate": exif_date,
                        "Quicktime:CreateDate": exif_date,
                        "Quicktime:DateTimeOriginal": exif_date,
                        "QuickTime:MediaCreateDate": exif_date,
                        "QuickTime:MediaModifyDate": exif_date,
                        "QuickTime:TrackCreateDate": exif_date,
                        "QuickTime:TrackModifyDate": exif_date,
                        "QuickTime:CreateDate": exif_date,
                        "QuickTime:ModifyDate": exif_date,
                    },
                    params=p,
                )
    except Exception as e:
        log.logger.warning("Could not set creation date of %s: %s", filename, e)
        return False
    log.logger.info("File %s creation date updated", filename)
    return True


def get_creation_date(filename: str) -> datetime.datetime | None:
    try:
        with ExifToolHelper(executable=util.get_exiftool(), encoding="utf-8") as et:
            for exif_data in et.get_metadata(filename):
                creation_date = util.get_creation_date(exif_data)
        return creation_date
    except FileNotFoundError:
        log.logger.warning("exiftool not found, cannot read creation date of %s", filename)
        return None
    except Exception as e:
        log.logger.warning("Could not read creation date of %s: %s", filename, e)
        return None


def get_exif(filename: str) -> None:
    with ExifToolHelper(executable=util.get_exiftool()) as et:
        for exif_data in et.get_metadata(filename):
            for k, v in exif_data.items():
                log.logger.info("EXIF - %s = %s", k, v)


def get_duration(filename: str) -> float:
    return VideoFile(filename).get_duration()
