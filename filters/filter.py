from typing import Union
from mediatools import log
import mediatools.utilities as util
import mediatools.exceptions as ex


class FilterError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message


VIDEO_TYPE = 0
AUDIO_TYPE = 1


class Filter:

    def __init__(self) -> None:
        self.inputs = []
        self.outputs = []

    def filter_type(self) -> int:
        return VIDEO_TYPE


class Simple(Filter):
    def __init__(self, filter_type=VIDEO_TYPE, stream_in=None, stream_out=None, filters=None):
        self.filter_type = filter_type
        self.stream_in = stream_in
        self.stream_out = stream_out
        if filters is None:
            self.filters = []
        elif isinstance(filters, list):
            self.filters = filters
        else:
            self.filters = [filters]

    def __str__(self):
        if not self.filters:
            return ""
        f = ",".join([str(f) for f in self.filters])
        s_in = "" if not self.stream_in else f"[{self.stream_in}]"
        s_out = "" if not self.stream_out else f"[{self.stream_out}]"
        t = "-af" if self.filter_type == AUDIO_TYPE else "-vf"
        return f'{t} "{s_in}{f}{s_out}"'

    def insert(self, pos, a_filter):
        self.filters.insert(pos, a_filter)

    def append(self, a_filter):
        self.filters.append(a_filter)

    def extend(self, filters):
        self.filters.extend(filters)


class Complex(Filter):
    def __init__(self, *inputs):
        self.inputs = list(inputs)
        self.serial_filters = None
        self.filtergraph = []

    def __str__(self):
        s = ""
        for f in self.filtergraph:
            for inp in f[0]:
                s += f"[{inp}]"
            s += str(f[1])
            s += f"[{f[2]}];"
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


class Fade(Simple):
    def __init__(self, start: float = 0.0, direction: str = "out", duration: float = 0.5, **kwargs) -> None:
        self.start = start
        self.direction = "in" if direction.lower() == "in" else "out"
        self.duration = duration
        self.alpha = kwargs.get("alpha", 1)

    def __str__(self) -> str:
        return f"fade=t={self.direction}:st={self.start}:d={self.duration}:alpha={self.alpha}"


class FadeIn(Fade):

    def __init__(self, duration: float = 0.5, **kwargs) -> None:
        super().__init__(start=0.0, direction="in", duration=duration, **kwargs)


class FadeOut(Fade):

    def __init__(self, duration: float = 0.5, **kwargs) -> None:
        super().__init__(start=self.inputs[0].duration() - duration, direction="in", duration=duration, **kwargs)


class Sar(Simple):

    def __init__(self, ratio: str) -> None:
        self.ratio = "/".join(ratio.split(":"))

    def __str__(self) -> str:
        return f"setsar={self.ratio}"


class Trim(Simple):

    def __init__(self, end: float, start: float = 0, **kwargs):
        self.start = start
        self.end = end
        self.params = kwargs.copy()

    def __str__(self) -> str:
        return f"trim=start={self.start}end={self.end}" + "".join([f"{k}={v}" for k, v in self.params.items()])


class Scale(Simple):
    """Scales a video - see https://ffmpeg.org/ffmpeg-filters.html#toc-scale-1"""

    def __init__(self, x: int, y: int, **kwargs) -> None:
        self.x = x
        self.y = y
        self.params = kwargs.copy()

    def __str__(self) -> str:
        return f"'scale={self.x}:{self.y}'" + "".join([f",{k}={v}" for k, v in self.params.items()])


class ScaleCuda(Scale):

    def __str__(self) -> str:
        return f"'scale={self.x}:{self.y}'" + "".join([f":{k}={v}" for k, v in self.params.items()])


class Crop(Simple):
    """Crops a video - see https://ffmpeg.org/ffmpeg-filters.html#toc-crop"""

    def __init__(self, x: int, y: int, x_formula: str = "x", y_formula: str = "y") -> None:
        self.x = x
        self.y = y
        self.x_formula = x_formula
        self.y_formula = y_formula

    def __str__(self) -> str:
        return "crop=" + ":".join([str(p) for p in (self.x, self.y, self.x_formula, self.y_formula)])


class Reverse(Simple):
    """Reverses a video clip see https://ffmpeg.org/ffmpeg-filters.html#toc-reverse"""

    def __str__(self) -> str:
        return "reverse"


class Areverse(Simple):
    """Reverses an audio clip See https://ffmpeg.org/ffmpeg-filters.html#toc-areverse"""

    def __str__(self) -> str:
        return "areverse"


class Volume(Simple):
    """Sets video / audio volume: see https://ffmpeg.org/ffmpeg-filters.html#toc-volume
    Can pass vol as a multiplier of current volume or absolute value like -6.0dB"""

    def __init__(self, vol: str, **kwargs) -> None:
        self.volume = vol
        self.params = kwargs.copy()

    def __str__(self) -> str:
        return f"volume={self.volume}" + "".join([f":{k}={v}" for k, v in self.params.items()])


class Overlay(Complex):
    """Overlays one video over another see https://ffmpeg.org/ffmpeg-filters.html#toc-overlay-1"""

    def __init__(self, x: str = "0", y: str = "0") -> None:
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f"overlay={self.x}:{self.y}"


class OverlayCuda(Overlay):
    """Overlays one video over another see https://ffmpeg.org/ffmpeg-filters.html#toc-overlay-1"""

    def __str__(self) -> str:
        return f"overlay_cuda={self.x}:{self.y}"


class Deshake(Simple):

    def __init__(self, rx: int = 32, ry: int = 32, **kwargs):
        self.params = {"x": -1, "y": -1, "w": -1, "h": -1}
        self.params.update(kwargs.copy())

    def __str__(self) -> str:
        return "deshake=" + ":".join([f"{k}={v}" for k, v in self.params.items()])


class Transpose(Simple):
    TRANSPOSITIONS = ("clock", "cclock", "clock_flip", "cclock_flip")
    ERR_ROTATION_ARG_1 = f"transposition must be one of {', '.join(TRANSPOSITIONS)}"
    ERR_ROTATION_ARG_2 = "transposition must be between 0 and 7"

    def __init__(self, transposition: Union[str, int] = 90) -> None:

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
        self.rotation = transposition

    def __str__(self) -> str:
        return f"transpose={self.rotation}"


class Rotate(Simple):
    """Rotates a video, see https://ffmpeg.org/ffmpeg-filters.html#toc-rotate"""

    def __init__(self, angle: str, **kwargs) -> None:
        """Example angle = 'PI/2'"""
        self.angle = angle
        self.params = kwargs.copy()

    def __str__(self):
        return "rotate=" + ":".join([f"{k}={v}" for k, v in self.params.items()])


# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------


def speed(target_speed):
    s = float(util.percent_or_absolute(target_speed))
    if s > 1:
        return select(f"not(mod(n,{s}))") + "," + setpts("N/FRAME_RATE/TB")
    else:
        return setpts(f"{1 / float(s)}*PTS")


def setpts(pts_formula):
    return f"setpts={pts_formula}"


def select(expr):
    return f"select='{expr}'"


def fade(direction: str = "in", start: float = 0.0, duration: float = 0.5, alpha: int = 1) -> str:
    return f"fade=t={direction}:st={start}:d={duration}:alpha={alpha}"


def fade_in(start: float = 0.0, duration: float = 0.5, alpha: int = 1) -> str:
    return fade("in", start, duration, alpha)


def fade_out(start: float = 0.0, duration: float = 0.5, alpha: int = 1):
    return fade("out", start, duration, alpha)


def __str_streams(streams):
    if isinstance(streams, (list, tuple)):
        s = "][".join(streams)
    elif isinstance(streams, str):
        s = f"{streams}"
    else:
        raise FilterError(f"Unexpected streams type {str(type(streams))}")
    return f"[{s}]"


def wrap_in_streams(filter_list, in_stream: str, out_stream: str) -> str:
    if isinstance(filter_list, str):
        s = filter_list
    elif isinstance(filter_list, (list, tuple)):
        s = ",".join(filter_list)
    else:
        raise FilterError(f"Unexpected filter_list type {type(filter_list)}")
    return f"[{in_stream}]{s}[{out_stream}]"


def in_out(filter_str, in_streams: str, out_streams: str) -> str:
    return f"{__str_streams(in_streams)}{filter_str}{__str_streams(out_streams)}"


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
        return f'-metadata {key}="{value}"'
    else:
        if track_type is None:
            track_type = "s:a"
        return f'-metadata:{track_type}:{track} {key}="{value}"'


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
