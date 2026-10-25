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

from __future__ import annotations

from mediatools import log
import mediatools.utilities as util
import mediatools.exceptions as ex

ROTATION_VALUES: tuple[str, ...] = ("clock", "cclock", "clock_flip", "cclock_flip")

ERR_ROTATION_ARG_1: str = f"rotation must be one of {', '.join(ROTATION_VALUES)}"
ERR_ROTATION_ARG_2: str = "rotation must be between 0 and 7"
ERR_ROTATION_ARG_3: str = "incorrect value for rotation"


class FilterError(Exception):
    def __init__(self, message: str) -> None:
        """Creates the error with its message"""
        super().__init__()
        self.message: str = message


VIDEO_TYPE: int = 0
AUDIO_TYPE: int = 1


class Simple(object):
    def __init__(
        self, filter_type: int = VIDEO_TYPE, stream_in: str | None = None, stream_out: str | None = None, filters: list | str | None = None
    ) -> None:
        """Creates a simple filter chain of a given type (video or audio), with optional input and output stream names"""
        self.filter_type: int = filter_type
        self.stream_in: str | None = stream_in
        self.stream_out: str | None = stream_out
        if filters is None:
            self.filters: list = []
        elif isinstance(filters, list):
            self.filters = filters
        else:
            self.filters = [filters]

    def __str__(self) -> str:
        """Returns the filters of the chain as an ffmpeg filter chain: [in]filter1,filter2[out]"""
        if not self.filters:
            return ""
        f = ",".join(self.filters)
        s_in = "" if self.stream_in is None else f"[{self.stream_in}]"
        s_out = "" if self.stream_out is None else f"[{self.stream_out}]"
        t = "-af" if self.filter_type == AUDIO_TYPE else "-vf"
        return f'{t} "{s_in}{f}{s_out}"'

    def insert(self, pos: int, a_filter: str) -> None:
        """Inserts a filter in the chain at a given position"""
        self.filters.insert(pos, a_filter)

    def append(self, a_filter: str) -> None:
        """Appends a filter at the end of the chain"""
        self.filters.append(a_filter)

    def extend(self, filters: list[str]) -> None:
        """Appends a list of filters at the end of the chain"""
        self.filters.extend(filters)


class Complex:
    def __init__(self, *inputs: object) -> None:
        """Creates a complex filter graph that applies to the given inputs"""
        self.inputs: list = list(inputs)
        self.serial_filters: object | None = None
        self.filtergraph: list = []

    def __str__(self) -> str:
        """Returns the filter graph as an ffmpeg -filter_complex option"""
        s = ""
        for f in self.filtergraph:
            s += "".join([f"[{inp}]" for inp in f[0]]) + str(f[1]) + f"[{f[2]}];"
        return f'-filter_complex "{s[:-1]}"'

    def format_inputs(self) -> str:
        """Returns the -i options of the inputs of the filter graph"""
        return " ".join([f'-i "{f.filename}"' for f in self.inputs])

    def insert_input(self, pos: int, an_input: object) -> None:
        """Inserts an input at a given position of the inputs of the filter graph"""
        self.inputs.insert(pos, an_input)

    def add_filtergraph(self, inputs: object, simple_filter: object) -> str:
        """Adds a filter to the graph, applied to the given input(s). Returns the name of the output stream of the filter"""
        outs = f"out{len(self.filtergraph)}"
        if not isinstance(inputs, (list, tuple)):
            inputs = [str(inputs)]
        log.logger.debug("Adding filtergraph %s, %s, %s", str(inputs), str(simple_filter), outs)
        self.filtergraph.append((inputs, simple_filter, outs))
        return outs


def __str_streams(streams: list | tuple | str) -> str:
    """Returns the labels of one or several streams, each one in square brackets: [a][b]"""
    if isinstance(streams, (list, tuple)):
        s = "[" + "][".join(streams) + "]"
    elif isinstance(streams, str):
        s = f"[{streams}]"
    else:
        raise FilterError(f"Unexpected streams type {type(streams)}")
    return s


def wrap_in_streams(filter_list: list | tuple | str, in_stream: str, out_stream: str) -> str:
    """Wraps a filter or a list of filters in an input and an output stream"""
    if isinstance(filter_list, str):
        s = filter_list
    elif isinstance(filter_list, (list, tuple)):
        s = ",".join(filter_list)
    else:
        raise FilterError(f"Unexpected filter_list type {type(filter_list)}")
    return f"[{in_stream}]{s}[{out_stream}]"


def in_out(filter_str: str, in_streams: list | tuple | str, out_streams: list | tuple | str) -> str:
    """Returns a filter with its input and output streams"""
    return f"{__str_streams(in_streams)}{filter_str}{__str_streams(out_streams)}"


def setsar(ratio: str) -> str:
    """Returns the filter that sets the sample aspect ratio (given as W:H)"""
    ratio = "/".join(ratio.split(":"))
    return f"setsar={ratio}"


def zoompan(x_formula: str, y_formula: str, z_formula: str, **kwargs: object) -> str:
    """Returns the zoompan filter with the formulas of the zoom and of the position, and other options"""
    opts = ":".join([f"{k}={v}" for k, v in kwargs.items()])
    return f"zoompan=z='{z_formula}':x='{x_formula}':y='{y_formula}':{opts}"


def format(pix_fmts: list[str] | str) -> str:  # noqa: A001
    """Returns the format filter with one or several pixel formats"""
    if isinstance(pix_fmts, list):
        s = "|".join(pix_fmts)
    elif isinstance(pix_fmts, str):
        s = pix_fmts
    else:
        raise FilterError(f"Unexpected pix_fmts {pix_fmts}")
    return f"format=pix_fmts={s}"


def overlay(x: int = 0, y: int = 0) -> str:
    """Returns the filter that overlays a stream on another at a position"""
    return f"overlay={x}:{y}"


def trim(duration: float | None = None, start: float | None = None, stop: float | None = None) -> str:
    """Returns the filter that keeps a part of the input, given by a duration or by a start and a stop time"""
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


def setpts(pts_formula: str) -> str:
    """Returns the setpts filter that sets the presentation timestamps of the frames with a formula"""
    return f"setpts={pts_formula}"


def scale(x: int, y: int) -> str:
    """Returns the filter that scales the input to a width and a height"""
    return f"scale={x}:{y}"


def crop(x: int, y: int, x_formula: str | None = None, y_formula: str | None = None) -> str:
    """Returns the filter that crops the input to a width and a height, optionally from positions given by formulas"""
    s = f"crop={x}:{y}"
    if x_formula is not None:
        s += f":{x_formula}"
    if y_formula is not None:
        s += f":{y_formula}"
    return s


def deshake(x: int = -1, y: int = -1, w: int = -1, h: int = -1, rx: int = 64, ry: int = 64) -> str:
    """Returns the filter that removes the shakiness of a video"""
    return f"deshake=x={x}:y={y}:w={w}:h={h}:rx={rx}:ry={ry}"


def vidstabdetect(shakiness: int = 8, accuracy: int = 15, trf_file: str = "transforms.trf") -> str:
    """Returns the filter that analyzes the shakiness of a video and saves it in a transforms file (first pass of the stabilization)"""
    return f"vidstabdetect=shakiness={shakiness}:accuracy={accuracy}:result='{trf_file}'"


def vidstabtransform(smoothing: int = 30, optzoom: int = 1, zoom: int = 0, trf_file: str = "transforms.trf") -> str:
    """Returns the filter that stabilizes a video from a transforms file (second pass of the stabilization)"""
    return f"vidstabtransform=smoothing={smoothing}:optzoom={optzoom}:zoom={zoom}:input='{trf_file}'"


def reverse() -> str:
    """Returns the filter that reverses a video"""
    return "reverse"


def areverse() -> str:
    """Returns the filter that reverses an audio stream"""
    return "areverse"


def volume(vol: str) -> str:
    """Sets video / audio volume
    Can pass vol as a multiplier of current volume or absolute value like -6.0dB"""
    return f"volume={vol}"


def rotate(rotation: int | str = 90) -> str:
    """Returns the transpose filter that rotates a video: 90 or -90 degrees, or a named transposition (clock, cclock, clock_flip, cclock_flip)"""
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


def speed(target_speed: str | float) -> str:
    """Returns the filters that change the speed of a video by a factor (1 = unchanged)"""
    s = float(util.percent_or_absolute(target_speed))
    if s > 1:
        expr = f"not(mod(n,{s})),{setpts('N/FRAME_RATE/TB')}"
        return f"select='{expr}'"
    return setpts(f"{1 / float(s)}*PTS")


def filtercomplex(filter_list: list[str] | None) -> str:
    """Returns the -filter_complex option for a list of filters, an empty string if there is none"""
    if filter_list is None or not filter_list:
        return ""
    sep = " "  # if platform.system() == 'Windows' else " \\\n"
    return f'-filter_complex "{sep}{("; " + sep).join(filter_list)}"'


def vfilter(filter_list: list[str] | None) -> str:
    """Returns the -vf option for a list of video filters, an empty string if there is none"""
    if filter_list is None or not filter_list:
        return ""
    return f'-vf "{",".join(filter_list)}"'


def afilter(filter_list: list[str] | None) -> str:
    """Returns the -af option for a list of audio filters, an empty string if there is none"""
    if filter_list is None or not filter_list:
        return ""
    return f'-af "{",".join(filter_list)}"'


def inputs_str(input_list: list[str]) -> str:
    """Returns the -i options of a list of input files"""
    sep = " "  # if platform.system() == 'Windows' else " \\\n"
    return sep.join([f'-i "{f}"' for f in input_list])


def format_options(opts: list[str] | None) -> str:
    """Returns a list of options as a string, an empty string if there is none"""
    return "" if opts is None else " ".join(opts)


def metadata(key: str, value: str, track: int | None = None, track_type: str | None = None) -> str:
    """Returns the -metadata option for a key and a value, optionally for a track"""
    if track is None:
        return f'-metadata {key}="{value}"'
    if track_type is None:
        track_type = "s:a"
    return f'-metadata:{track_type}:{track} {key}="{value}"'


def vcodec(codec: str) -> str:
    """Returns the -vcodec option for a video codec"""
    return f"-vcodec {codec}"


def acodec(codec: str) -> str:
    """Returns the -acodec option for an audio codec"""
    return f"-acodec {codec}"


def disposition(default_track: int, nb_tracks: int) -> str:
    """Returns the -disposition options that set one audio track as the default one among several"""
    # -disposition:a:0 default -disposition:a:1
    return " ".join([f"-disposition:a:{t} {'default' if t == default_track else 'none'}" for t in range(nb_tracks)])


def afade_in(start: float = 0, duration: float = 1.0) -> str:
    """Returns the filter that fades in an audio stream"""
    return f"afade=t=in:st={start}:d={duration}"


def afade_out(start: float = 0, duration: float = 1.0) -> str:
    """Returns the filter that fades out an audio stream"""
    return f"afade=t=out:st={start}:d={duration}"


def afade(fade_type: str, start: float = 0, duration: float = 1.0) -> str:
    """Returns the filter that fades in or out ('in' or 'out') an audio stream. Raises a FilterError for any other type"""
    if fade_type not in ("in", "out"):
        raise FilterError(f"afade type must be 'in' or 'out', got '{fade_type}'")
    return f"afade=t={fade_type}:st={start}:d={duration}"


def hw_accel_input(**kwargs: object) -> str:
    """Returns the ffmpeg options that decode the input with the GPU if hw_accel is set, an empty string otherwise"""
    return "-hwaccel cuvid -c:v h264_cuvid" if kwargs.get("hw_accel", False) else ""


def hw_accel_output(**kwargs: object) -> str:
    """Returns the ffmpeg options that encode the output with the GPU if hw_accel is set, an empty string otherwise"""
    return "-c:v h264_nvenc" if kwargs.get("hw_accel", False) else ""
