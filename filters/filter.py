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

from __future__ import annotations

from mediatools import log
import mediatools.utilities as util
import mediatools.exceptions as ex


class FilterError(Exception):
    def __init__(self, message: str) -> None:
        """Creates the error with its message"""
        super().__init__()
        self.message: str = message


VIDEO_TYPE: int = 0
AUDIO_TYPE: int = 1


class Filter:

    def __init__(self) -> None:
        """Creates a filter with no input and no output"""
        self.inputs: list = []
        self.outputs: list = []

    def filter_type(self) -> int:
        """Returns the type of the filter (video or audio)"""
        return VIDEO_TYPE


class Simple(Filter):
    def __init__(
        self, filter_type: int = VIDEO_TYPE, stream_in: str | None = None, stream_out: str | None = None, filters: list | str | None = None
    ) -> None:
        """Creates a simple filter chain of a given type (video or audio), with optional input and output stream names"""
        super().__init__()
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
        f = ",".join([str(f) for f in self.filters])
        s_in = "" if not self.stream_in else f"[{self.stream_in}]"
        s_out = "" if not self.stream_out else f"[{self.stream_out}]"
        t = "-af" if self.filter_type == AUDIO_TYPE else "-vf"
        return f'{t} "{s_in}{f}{s_out}"'

    def insert(self, pos: int, a_filter: object) -> None:
        """Inserts a filter in the chain at a given position"""
        self.filters.insert(pos, a_filter)

    def append(self, a_filter: object) -> None:
        """Appends a filter at the end of the chain"""
        self.filters.append(a_filter)

    def extend(self, filters: list) -> None:
        """Appends a list of filters at the end of the chain"""
        self.filters.extend(filters)


class Complex(Filter):
    def __init__(self, *inputs: object) -> None:
        """Creates a complex filter graph that applies to the given inputs"""
        super().__init__()
        self.inputs: list = list(inputs)
        self.serial_filters: object | None = None
        self.filtergraph: list = []

    def __str__(self) -> str:
        """Returns the filter graph as an ffmpeg -filter_complex option"""
        s = ""
        for f in self.filtergraph:
            for inp in f[0]:
                s += f"[{inp}]"
            s += str(f[1])
            s += f"[{f[2]}];"
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


class Fade(Simple):
    def __init__(self, start: float = 0.0, direction: str = "out", duration: float = 0.5, **kwargs: object) -> None:
        """Creates a fade in or out filter, starting at a given time and lasting a given duration"""
        self.start: float = start
        self.direction: str = "in" if direction.lower() == "in" else "out"
        self.duration: float = duration
        self.alpha: int = kwargs.get("alpha", 1)

    def __str__(self) -> str:
        """Returns the ffmpeg fade filter"""
        return f"fade=t={self.direction}:st={self.start}:d={self.duration}:alpha={self.alpha}"


class FadeIn(Fade):

    def __init__(self, duration: float = 0.5, **kwargs: object) -> None:
        """Creates a fade in filter, from the start of the video"""
        super().__init__(start=0.0, direction="in", duration=duration, **kwargs)


class FadeOut(Fade):
    """Fades out during the duration that starts at start (the end of the video minus the duration)"""

    def __init__(self, start: float = 0.0, duration: float = 0.5, **kwargs: object) -> None:
        """Creates a fade out filter, starting at a given time"""
        super().__init__(start=start, direction="out", duration=duration, **kwargs)


class Sar(Simple):

    def __init__(self, ratio: str) -> None:
        """Creates a filter that sets the sample aspect ratio (given as W:H)"""
        self.ratio: str = "/".join(ratio.split(":"))

    def __str__(self) -> str:
        """Returns the ffmpeg setsar filter"""
        return f"setsar={self.ratio}"


class Trim(Simple):

    def __init__(self, end: float, start: float = 0, **kwargs: object) -> None:
        """Creates a filter that keeps the part of the input between a start and an end time"""
        self.start: float = start
        self.end: float = end
        self.params: dict = kwargs.copy()

    def __str__(self) -> str:
        """Returns the ffmpeg trim filter"""
        return f"trim=start={self.start}:end={self.end}" + "".join([f":{k}={v}" for k, v in self.params.items()])


class Scale(Simple):
    """Scales a video - see https://ffmpeg.org/ffmpeg-filters.html#toc-scale-1"""

    def __init__(self, x: int, y: int, **kwargs: object) -> None:
        """Creates a filter that scales the input to a width and a height"""
        self.x: int = x
        self.y: int = y
        self.params: dict = kwargs.copy()

    def __str__(self) -> str:
        """Returns the ffmpeg scale filter"""
        return f"'scale={self.x}:{self.y}'" + "".join([f",{k}={v}" for k, v in self.params.items()])


class ScaleCuda(Scale):

    def __str__(self) -> str:
        """Returns the ffmpeg scale filter, with the parameters in the format of the GPU filters"""
        return f"'scale={self.x}:{self.y}'" + "".join([f":{k}={v}" for k, v in self.params.items()])


class Crop(Simple):
    """Crops a video - see https://ffmpeg.org/ffmpeg-filters.html#toc-crop"""

    def __init__(self, x: int, y: int, x_formula: str = "x", y_formula: str = "y") -> None:
        """Creates a filter that crops the input to a width and a height, from positions given by formulas"""
        self.x: int = x
        self.y: int = y
        self.x_formula: str = x_formula
        self.y_formula: str = y_formula

    def __str__(self) -> str:
        """Returns the ffmpeg crop filter"""
        return "crop=" + ":".join([str(p) for p in (self.x, self.y, self.x_formula, self.y_formula)])


class Reverse(Simple):
    """Reverses a video clip see https://ffmpeg.org/ffmpeg-filters.html#toc-reverse"""

    def __str__(self) -> str:
        """Returns the ffmpeg reverse filter"""
        return "reverse"


class Areverse(Simple):
    """Reverses an audio clip See https://ffmpeg.org/ffmpeg-filters.html#toc-areverse"""

    def __str__(self) -> str:
        """Returns the ffmpeg areverse filter"""
        return "areverse"


class Volume(Simple):
    """Sets video / audio volume: see https://ffmpeg.org/ffmpeg-filters.html#toc-volume
    Can pass vol as a multiplier of current volume or absolute value like -6.0dB"""

    def __init__(self, vol: str, **kwargs: object) -> None:
        """Creates a filter that changes the volume of an audio stream"""
        self.volume: str = vol
        self.params: dict = kwargs.copy()

    def __str__(self) -> str:
        """Returns the ffmpeg volume filter"""
        return f"volume={self.volume}" + "".join([f":{k}={v}" for k, v in self.params.items()])


class Overlay(Complex):
    """Overlays one video over another see https://ffmpeg.org/ffmpeg-filters.html#toc-overlay-1"""

    def __init__(self, x: str = "0", y: str = "0") -> None:
        """Creates a filter that overlays a stream on another at a position"""
        self.x: str = x
        self.y: str = y

    def __str__(self) -> str:
        """Returns the ffmpeg overlay filter"""
        return f"overlay={self.x}:{self.y}"


class OverlayCuda(Overlay):
    """Overlays one video over another see https://ffmpeg.org/ffmpeg-filters.html#toc-overlay-1"""

    def __str__(self) -> str:
        """Returns the ffmpeg overlay_cuda filter (GPU version of overlay)"""
        return f"overlay_cuda={self.x}:{self.y}"


class Deshake(Simple):

    def __init__(self, rx: int = 32, ry: int = 32, **kwargs: object) -> None:
        """Creates a filter that removes the shakiness of a video, within a search range of rx and ry pixels"""
        self.params: dict[str, int] = {"x": -1, "y": -1, "w": -1, "h": -1, "rx": rx, "ry": ry}
        self.params.update(kwargs.copy())

    def __str__(self) -> str:
        """Returns the ffmpeg deshake filter"""
        return "deshake=" + ":".join([f"{k}={v}" for k, v in self.params.items()])


def deshake(rx: int = 32, ry: int = 32, **kwargs: object) -> Deshake:
    """Returns the deshake filter with a search range of rx and ry pixels"""
    return Deshake(rx=rx, ry=ry, **kwargs)


def crop(x: int, y: int, x_formula: str = "x", y_formula: str = "y") -> Crop:
    """Returns the crop filter that crops to a width and a height, from positions given by formulas"""
    return Crop(x=x, y=y, x_formula=x_formula, y_formula=y_formula)


class Transpose(Simple):
    TRANSPOSITIONS: tuple[str, ...] = ("clock", "cclock", "clock_flip", "cclock_flip")
    ERR_ROTATION_ARG_1: str = f"transposition must be one of {', '.join(TRANSPOSITIONS)}"
    ERR_ROTATION_ARG_2: str = "transposition must be between 0 and 7"

    def __init__(self, transposition: str | int = 90) -> None:
        """Creates a filter that transposes (rotates or flips) the input: a name (clock, cclock, clock_flip or cclock_flip), a number from 0 to 7, or
        an angle (90 or -90)"""
        if isinstance(transposition, str):
            if transposition not in Transpose.TRANSPOSITIONS:
                raise ex.InputError(Transpose.ERR_ROTATION_ARG_1, "transpose")
        else:
            if transposition == 90:
                transposition = 1
            if transposition == -90:
                transposition = 2
            if transposition < 0 or transposition > 7:
                raise ex.InputError(Transpose.ERR_ROTATION_ARG_2, "transpose")
        self.rotation: str | int = transposition

    def __str__(self) -> str:
        """Returns the ffmpeg transpose filter"""
        return f"transpose={self.rotation}"


class Rotate(Simple):
    """Rotates a video, see https://ffmpeg.org/ffmpeg-filters.html#toc-rotate"""

    def __init__(self, angle: str, **kwargs: object) -> None:
        """Example angle = 'PI/2'"""
        self.angle: str = angle
        self.params: dict = kwargs.copy()

    def __str__(self) -> str:
        """Returns the ffmpeg rotate filter"""
        return f"rotate={self.angle}" + "".join([f":{k}={v}" for k, v in self.params.items()])


# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------


def speed(target_speed: str | float) -> str:
    """Returns the filters that change the speed of a video by a factor (1 = unchanged): frames are dropped to accelerate and stretched to slow down
    Returns the filters that change the speed of a video by a factor (1 = unchanged): frames are dropped to accelerate and stretched to slow down"""
    s = float(util.percent_or_absolute(target_speed))
    if s > 1:
        return select(f"not(mod(n,{s}))") + "," + setpts("N/FRAME_RATE/TB")
    return setpts(f"{1 / float(s)}*PTS")


def setpts(pts_formula: str) -> str:
    """Returns the setpts filter that sets the presentation timestamps of the frames with a formula"""
    return f"setpts={pts_formula}"


def select(expr: str) -> str:
    """Returns the select filter that keeps the frames for which an expression is true"""
    return f"select='{expr}'"


def fade(direction: str = "in", start: float = 0.0, duration: float = 0.5, alpha: int = 1) -> str:
    """Returns the fade filter (fade in or out) as a string"""
    return f"fade=t={direction}:st={start}:d={duration}:alpha={alpha}"


def fade_in(start: float = 0.0, duration: float = 0.5, alpha: int = 1) -> str:
    """Returns the fade in filter as a string"""
    return fade("in", start, duration, alpha)


def fade_out(start: float = 0.0, duration: float = 0.5, alpha: int = 1) -> str:
    """Returns the fade out filter as a string"""
    return fade("out", start, duration, alpha)


def __str_streams(streams: list | tuple | str) -> str:
    """Returns the labels of one or several streams, each one in square brackets: [a][b]"""
    if isinstance(streams, (list, tuple)):
        s = "][".join(streams)
    elif isinstance(streams, str):
        s = f"{streams}"
    else:
        raise FilterError(f"Unexpected streams type {type(streams)!s}")
    return f"[{s}]"


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


def hw_accel_input(**kwargs: object) -> str:
    """Returns the ffmpeg options that decode the input with the GPU if hw_accel is set, an empty string otherwise"""
    return "-hwaccel cuvid -c:v h264_cuvid" if kwargs.get("hw_accel", False) else ""


def hw_accel_output(**kwargs: object) -> str:
    """Returns the ffmpeg options that encode the output with the GPU if hw_accel is set, an empty string otherwise"""
    return "-c:v h264_nvenc" if kwargs.get("hw_accel", False) else ""
