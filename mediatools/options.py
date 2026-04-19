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

"""
This file encapsulates
- various constants
- data structures and
- translation functions
used in several places
in mediatools library
"""

OPT_FMT: str = '-{} "{}"'

CODECS: dict[str, str] = {"h264": "libx264", "x264": "libx264", "h265": "libx265", "x265": "libx265", "aac": "aac", "mp3": "libmp3lame", "copy": "copy"}

HW_ACCEL_CODECS: dict[str, str] = {
    "h264": "h264_nvenc",
    "h265": "hevc_nvenc",
    "x264": "h264_nvenc",
    "x265": "hevc_nvenc",
    "aac": "aac",
    "mp3": "libmp3lame",
    "copy": "copy",
}


class OptionFfmpeg:
    """Documents supported ffmpeg options"""

    FORMAT: str = "f"
    RESOLUTION: str = "s"
    VCODEC: str = "vcodec"
    VCODEC2: str = "c:v"
    VCODEC3: str = "codec:v"
    ACODEC: str = "acodec"
    ACODEC2: str = "c:a"
    ACODEC3: str = "codec:a"
    VBITRATE: str = "b:v"
    ABITRATE: str = "b:a"
    FPS: str = "r"
    ASPECT: str = "aspect"
    DEINTERLACE: str = "deinterlace"
    ACHANNEL: str = "ac"
    VFILTER: str = "vf"
    START: str = "ss"
    STOP: str = "to"
    MUTE: str = "an"
    VMUTE: str = "vn"
    SAMPLERATE: str = "ar"


class Option:
    """Documents supported audio-video-tools encoding options"""

    FORMAT: str = "format"
    RESOLUTION: str = "resolution"
    VCODEC: str = "vcodec"
    ACODEC: str = "acodec"
    VBITRATE: str = "vbitrate"
    ABITRATE: str = "abitrate"
    WIDTH: str = "width"
    HEIGHT: str = "height"
    FPS: str = "fps"
    ASPECT: str = "aspect"
    DEINTERLACE: str = "deinterlace"
    ACHANNEL: str = "achannels"
    VFILTER: str = "vfilter"
    START: str = "start"
    STOP: str = "stop"
    ASAMPLING: str = "asamplerate"
    AUTHOR: str = "author"
    TITLE: str = "title"
    ALBUM: str = "album"
    YEAR: str = "year"
    TRACK: str = "track"
    GENRE: str = "genre"
    DURATION: str = "duration"
    LANGUAGE: str = "language"
    MUTE: str = "mute"
    VMUTE: str = "vmute"
    SAMPLERATE: str = "samplerate"


M2F_MAPPING: dict[str, str] = {
    Option.FORMAT: OptionFfmpeg.FORMAT,
    Option.VCODEC: OptionFfmpeg.VCODEC,
    Option.VBITRATE: OptionFfmpeg.VBITRATE,
    Option.ACODEC: OptionFfmpeg.ACODEC,
    Option.ABITRATE: OptionFfmpeg.ABITRATE,
    Option.FPS: OptionFfmpeg.FPS,
    Option.ASPECT: OptionFfmpeg.ASPECT,
    Option.RESOLUTION: OptionFfmpeg.RESOLUTION,
    Option.DEINTERLACE: OptionFfmpeg.DEINTERLACE,
    Option.ACHANNEL: OptionFfmpeg.ACHANNEL,
    Option.VFILTER: OptionFfmpeg.VFILTER,
    Option.START: OptionFfmpeg.START,
    Option.STOP: OptionFfmpeg.STOP,
    Option.MUTE: OptionFfmpeg.MUTE,
    Option.VMUTE: OptionFfmpeg.VMUTE,
}

F2M_MAPPING: dict[str, str] = {}
for k, v in M2F_MAPPING.items():
    F2M_MAPPING[v] = k
F2M_MAPPING[OptionFfmpeg.ACODEC2] = Option.ACODEC
F2M_MAPPING[OptionFfmpeg.ACODEC3] = Option.ACODEC
F2M_MAPPING[OptionFfmpeg.VCODEC2] = Option.VCODEC
F2M_MAPPING[OptionFfmpeg.VCODEC3] = Option.VCODEC


def media2ffmpeg(options: dict | None) -> dict:
    # Returns ffmpeg cmd options dict from media options dict
    import mediatools.utilities as util

    if options is None:
        return {}
    ffopts = {}
    for key in M2F_MAPPING:
        if key in options and options[key] is not None:
            ffopts[M2F_MAPPING[key]] = options[key]
    return util.remove_nones(ffopts)


def ffmpeg2media(options: dict | None) -> dict:
    # Returns ffmpeg cmd options dict from media options dict
    import mediatools.utilities as util

    if options is None:
        return {}
    mopts = {}
    for key in M2F_MAPPING:
        if key in options and options[key] is not None:
            mopts[M2F_MAPPING[key]] = options[key]
    return util.remove_nones(mopts)
