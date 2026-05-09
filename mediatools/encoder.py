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

from __future__ import annotations

import mediatools.options as opt


LANGUAGE_MAPPING: dict[str, str] = {"fre": "French", "eng": "English"}


class Encoder:
    """Encoder abstraction"""

    SETTINGS: list[str] = [
        "format",
        "vcodec",
        "vbitrate",
        "acodec",
        "abitrate",
        "fps",
        "aspect",
        "vsize",
        "deinterlace",
        "achannel",
        "asample",
        "vfilter",
        "start",
        "stop",
    ]

    def __init__(self, **kwargs) -> None:
        self.format: str | None = None
        self.aspect: str | None = None
        self.resolution: str | None = None
        self.vcodec: str = "copy"
        self.vbitrate: int | None = None
        self.video_fps: float | None = None
        self.abitrate: int | None = None
        self.acodec: str = "copy"
        self.audio_language: str | None = None
        self.audio_sample_rate: int | None = None
        self.start: float | str | None = None
        self.stop: float | str | None = None
        self.vfilters: list[str] = []
        self.add_settings(**kwargs)
        self.others: dict = {}

    def add_settings(self, **kwargs) -> None:
        kwsettings = {}
        for k in kwargs:
            if k in Encoder.SETTINGS and kwargs[k] is not None:
                kwsettings[k] = kwargs[k]
        if "vcodec" in kwsettings:
            self.vcodec = kwsettings[opt.Option.VCODEC]
        if "vbitrate" in kwsettings:
            self.vbitrate = kwsettings[opt.Option.VBITRATE]
        if "acodec" in kwsettings:
            self.acodec = kwsettings[opt.Option.ACODEC]
        if "abitrate" in kwsettings:
            self.abitrate = kwsettings[opt.Option.ABITRATE]
        if "aspect" in kwsettings:
            self.aspect = kwsettings[opt.Option.ASPECT]
        if "resolution" in kwsettings:
            self.resolution = kwsettings[opt.Option.RESOLUTION]
        if "start" in kwsettings:
            self.start = kwsettings[opt.Option.START]
        if "stop" in kwsettings:
            self.start = kwsettings[opt.Option.STOP]
        if "format" in kwsettings:
            self.format = kwsettings[opt.Option.FORMAT]

    def set_format(self, fmt: str) -> None:
        self.format = fmt

    def add_vfilter(self, vfilter: str) -> None:
        self.vfilters.append(vfilter)

    def get_vfilters_string(self) -> str:
        cmd = ""
        for f in self.vfilters:
            cmd = cmd + '-filter:v "%s" ' % f
        return cmd.strip()

    def add_crop_filter(self, width: int, height: int, top: int, left: int) -> None:
        self.add_vfilter("crop={0}:{1}:{2}:{3}".format(width, height, top, left))

    def add_deshake_filter(self, width: int, height: int) -> None:
        # ffmpeg -i <in> -f mp4 -vf deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=16 -b:v 2048k <out>
        self.add_vfilter("deshake=x=-1:y=-1:w=-1:h=-1:rx={0}:ry={1}".format(width, height))

    def add_fade_filter(self, fade_d: float, start: float | None = None, stop: float | None = None) -> None:
        if start is None:
            start = self.start
        if start is None:
            start = 0
        if stop is None:
            stop = self.stop
        fmt = "fade=type={0}:duration={1}:start_time={2}"
        fader = fmt.format("in", fade_d, start) + "," + fmt.format("out", fade_d, stop - fade_d)
        self.add_vfilter(fader)

    def ffmpeg_opts(self) -> str:
        """Builds string corresponding to ffmpeg conventions"""
        options = vars(self)
        cmd = ""
        for option in options.keys():
            if options[option] is not None and not isinstance(options[option], list):
                cmd = cmd + " -{0} {1}".format(opt.M2F_MAPPING[option], options[option])
        cmd = cmd + " " + self.get_vfilters_string()
        return cmd.strip()
