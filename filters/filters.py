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

from typing import Union
from mediatools import log
import mediatools.utilities as util
import mediatools.exceptions as ex

ROTATION_VALUES = ("clock", "cclock", "clock_flip", "cclock_flip")

ERR_ROTATION_ARG_1 = f"rotation must be one of {', '.join(ROTATION_VALUES)}"
ERR_ROTATION_ARG_2 = "rotation must be between 0 and 7"
ERR_ROTATION_ARG_3 = "incorrect value for rotation"


class FilterError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message


VIDEO_TYPE = 0
AUDIO_TYPE = 1


class Simple(object):
    def __init__(self, filter_type=VIDEO_TYPE, stream_in=None, stream_out=None, filters=None) -> None:
        self.filter_type = filter_type
        self.stream_in = stream_in
        self.stream_out = stream_out
        if filters is None:
            self.filters = []
        elif isinstance(filters, list):
            self.filters = filters
        else:
            self.filters = [filters]

    def __str__(self) -> str:
        if not self.filters:
            return ""
        f = ",".join(self.filters)
        s_in = "" if self.stream_in is None else f"[{self.stream_in}]"
        s_out = "" if self.stream_out is None else f"[{self.stream_out}]"
        t = "-af" if self.filter_type == AUDIO_TYPE else "-vf"
        return f'{t} "{s_in}{f}{s_out}"'

    def insert(self, pos, a_filter):
        self.filters.insert(pos, a_filter)

    def append(self, a_filter):
        self.filters.append(a_filter)

    def extend(self, filters):
        self.filters.extend(filters)


class Complex:
    def __init__(self, *inputs):
        self.inputs = list(inputs)
        self.serial_filters = None
        self.filtergraph = []

    def __str__(self):
        s = ""
        for f in self.filtergraph:
            s += "".join([f"[{inp}]" for inp in f[0]]) + str(f[1]) + f"[{f[2]}];"
        return f'-filter_complex "{s[:-1]}"'

    def format_inputs(self):
        return " ".join([f'-i "{f.filename}"' for f in self.inputs])

    def insert_input(self, pos, an_input):
        self.inputs.insert(pos, an_input)

    def add_filtergraph(self, inputs, simple_filter):
        outs = f"out{len(self.filtergraph)}"
        if not isinstance(inputs, (list, tuple)):
            inputs = [str(inputs)]
        log.logger.debug("Adding filtergraph %s, %s, %s", str(inputs), str(simple_filter), outs)
        self.filtergraph.append((inputs, simple_filter, outs))
        return outs


def __str_streams(streams):
    if isinstance(streams, (list, tuple)):
        s = "[" + "][".join(streams) + "]"
    elif isinstance(streams, str):
        s = f"[{streams}]"
    else:
        raise FilterError(f"Unexpected streams type {type(streams)}")
    return s


def wrap_in_streams(filter_list, in_stream, out_stream):
    if isinstance(filter_list, str):
        s = filter_list
    elif isinstance(filter_list, (list, tuple)):
        s = ",".join(filter_list)
    else:
        raise FilterError(f"Unexpected filter_list type {type(filter_list)}")
    return f"[{in_stream}]{s}[{out_stream}]"


def in_out(filter_str, in_streams, out_streams):
    return f"{__str_streams(in_streams)}{filter_str}{__str_streams(out_streams)}"


def setsar(ratio):
    ratio = "/".join(ratio.split(":"))
    return f"setsar={ratio}"


def zoompan(x_formula: str, y_formula: str, z_formula: str, **kwargs):
    opts = ":".join([f"{k}={v}" for k, v in kwargs])
    return f"zoompan=z='{z_formula}':x='{x_formula}':y='{y_formula}':{opts}"


def format(pix_fmts) -> str:
    if isinstance(pix_fmts, list):
        s = "|".join(pix_fmts)
    elif isinstance(pix_fmts, str):
        s = pix_fmts
    else:
        raise FilterError(f"Unexpected pix_fmts {pix_fmts}")
    return f"format=pix_fmts={s}"


def overlay(x: int = 0, y: int = 0):
    return f"overlay={x}:{y}"


def trim(duration: float = None, start: float = None, stop: float = None) -> str:
    if duration is None and (start is None or stop is None):
        raise FilterError("No duration, start or stop for trim filter")
    s = "trim="
    if duration is not None:
        s += f"duration={duration}"
    if start is not None:
        s += f"start={start}"
    if stop is not None:
        s += f"stop={stop}"
    return s


def setpts(pts_formula) -> str:
    return f"setpts={pts_formula}"


def scale(x: int, y: int) -> str:
    return f"scale={x}:{y}"


def crop(x: int, y: int, x_formula: str = None, y_formula: str = None) -> str:
    s = f"crop={x}:{y}"
    if x_formula is not None:
        s += f":{x_formula}"
    if y_formula is not None:
        s += f":{y_formula}"
    return s


def deshake(x: int = -1, y: int = -1, w: int = -1, h: int = -1, rx: int = 64, ry: int = 64) -> str:
    return f"deshake=x={x}:y={y}:w={w}:h={h}:rx={rx}:ry={ry}"


def reverse():
    return "reverse"


def areverse():
    return "areverse"


def volume(vol: str) -> str:
    """Sets video / audio volume
    Can pass vol as a multiplier of current volume or absolute value like -6.0dB"""
    return f"volume={vol}"


def rotate(rotation: Union[int, str] = 90) -> str:
    if isinstance(rotation, str) and rotation not in ROTATION_VALUES:
        raise ex.InputError(ERR_ROTATION_ARG_1, "rotate")
    if not isinstance(rotation, int):
        raise ex.InputError(ERR_ROTATION_ARG_3, "rotate")
    rotation = int(rotation)
    if rotation == 90:
        rotation = 1
    if rotation == -90:
        rotation = 2
    if rotation < 0 or rotation > 7:
        raise ex.InputError(ERR_ROTATION_ARG_2, "rotate")
    return f"transpose={rotation}"


def speed(target_speed) -> str:
    s = float(util.percent_or_absolute(target_speed))
    if s > 1:
        expr = f"not(mod(n,{s})),{setpts('N/FRAME_RATE/TB')}"
        return f"select='{expr}'"
    else:
        return setpts(f"{1 / float(s)}*PTS")


def filtercomplex(filter_list):
    if filter_list is None or not filter_list:
        return ""
    sep = " "  # if platform.system() == 'Windows' else " \\\n"
    return f'-filter_complex "{sep}{("; " + sep).join(filter_list)}"'


def vfilter(filter_list):
    if filter_list is None or not filter_list:
        return ""
    return f'-vf "{",".join(filter_list)}"'


def afilter(filter_list):
    if filter_list is None or not filter_list:
        return ""
    return f'-af "{",".join(filter_list)}"'


def inputs_str(input_list):
    sep = " "  # if platform.system() == 'Windows' else " \\\n"
    return sep.join([f'-i "{f}"' for f in input_list])


def format_options(opts):
    return "" if opts is None else " ".join(opts)


def metadata(key, value, track=None, track_type=None):
    if track is None:
        return '-metadata {}="{}"'.format(key, value)
    else:
        if track_type is None:
            track_type = "s:a"
        return '-metadata:{}:{} {}="{}"'.format(track_type, track, key, value)


def vcodec(codec: str) -> str:
    return f"-vcodec {codec}"


def acodec(codec: str) -> str:
    return f"-acodec {codec}"


def disposition(default_track: int, nb_tracks: int) -> str:
    # -disposition:a:0 default -disposition:a:1
    return " ".join([f"-disposition:a:{t} {'default' if t == default_track else 'none'}" for t in range(nb_tracks)])


def hw_accel_input(**kwargs) -> str:
    return "-hwaccel cuvid -c:v h264_cuvid" if kwargs.get("hw_accel", False) else ""


def hw_accel_output(**kwargs) -> str:
    return "-c:v h264_nvenc" if kwargs.get("hw_accel", False) else ""
