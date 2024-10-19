
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
            return ''
        f = ','.join(self.filters)
        s_in = '' if self.stream_in is None else '[{}]'.format(self.stream_in)
        s_out = '' if self.stream_in is None else '[{}]'.format(self.stream_out)
        t = '-af' if self.filter_type == AUDIO_TYPE else '-vf'
        return '{} "{}{}{}"'.format(t, s_in, f, s_out)

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
        s = ''
        for f in self.filtergraph:
            for inp in f[0]:
                s += '[{}]'.format(inp)
            s += str(f[1])
            s += '[{}];'.format(f[2])
        return '-filter_complex "{}"'.format(s[:-1])

    def format_inputs(self):
        return ' '.join(['-i "{}"'.format(f.filename) for f in self.inputs])

    def insert_input(self, pos, an_input):
        self.inputs.insert(pos, an_input)

    def add_filtergraph(self, inputs, simple_filter):
        outs = 'out{}'.format(len(self.filtergraph))
        if not isinstance(inputs, (list, tuple)):
            inputs = [str(inputs)]
        log.logger.debug('Adding filtergraph %s, %s, %s', str(inputs), str(simple_filter), outs)
        self.filtergraph.append((inputs, simple_filter, outs))
        return outs


class Fade(Simple):
    def __init__(self, start: float = 0.0, direction: str = 'out', duration: float = 0.5, **kwargs) -> None:
        self.start = start
        self.direction = 'in' if direction.lower() == 'in' else 'out'
        self.duration = duration
        self.alpha = kwargs.get('alpha', 1)

    def __str__(self) -> str:
        return f"fade=t={self.direction}:st={self.start}:d={self.duration}:alpha={self.alpha}"

class FadeIn(Fade):

    def __init__(self, duration: float = 0.5, **kwargs) -> None:
        super().__init__(start=0.0, direction='in', duration=duration, **kwargs)

class FadeOut(Fade):

    def __init__(self, duration: float = 0.5, **kwargs) -> None:
        super().__init__(start=self.inputs[0].duration() - duration, direction='in', duration=duration, **kwargs)

class Sar(Simple):

    def __init__(self, ratio: str) -> None:
        self.ratio = '/'.join(ratio.split(':'))

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
    def __init__(self, x: int, y: int, x_formula: str = 'x', y_formula: str = 'y') -> None:
        self.x = x
        self.y = y
        self.x_formula = x_formula
        self.y_formula = y_formula

    def __str__(self) -> str:
        return f"crop=" + ":".join([str(p) for p in (self.x, self.y, self.x_formula, self.y_formula)])

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
    Can pass vol as a multiplier of current volume or absolute value like -6.0dB """

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
        self.params = {'x': -1, 'y': -1, 'w': -1, 'h': -1}
        self.params.update(kwargs.copy())

    def __str__(self) -> str:
        return "deshake=" + ":".join([ f"{k}={v}" for k, v in self.params.items()])


class Transpose(Simple):
    TRANSPOSITIONS = ('clock', 'cclock', 'clock_flip', 'cclock_flip')
    ERR_ROTATION_ARG_1 = f'transposition must be one of {', '.join(TRANSPOSITIONS)}'
    ERR_ROTATION_ARG_2 = 'transposition must be between 0 and 7'

    def __init__(self, transposition: str | int = 90) -> None:

        if isinstance(transposition, str):
            if transposition not in Transpose.TRANSPOSITIONS:
                raise ex.InputError(Transpose.ERR_ROTATION_ARG_1, 'transpose')
        else:
            if transposition == 90:
                transposition = 1
            if transposition == -90:
                transposition = 2
            if transposition < 0 or transposition > 7:
                raise ex.InputError(Transpose.ERR_ROTATION_ARG_2, 'transpose')
        self.rotation = transposition

    def __str__(self) -> str:
        return f"transpose={self.rotation}"

class Rotate(Simple):
    """ Rotates a video, see https://ffmpeg.org/ffmpeg-filters.html#toc-rotate """
    def __init__(self, angle: str, **kwargs) -> None:
        """ Example angle = 'PI/2' """
        self.angle = angle
        self.params = kwargs.copy()

    def __str__(self):
        return "rotate=" + ":".join([ f"{k}={v}" for k, v in self.params.items()])


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

def speed(target_speed):
    s = float(util.percent_or_absolute(target_speed))
    if s > 1:
        return select('not(mod(n,{}))'.format(s)) + ',' + setpts('N/FRAME_RATE/TB')
    else:
        return setpts("{}*PTS".format(1 / float(s)))

def setpts(pts_formula):
    return "setpts={}".format(pts_formula)


def select(expr):
    return "select='{}'".format(expr)




def __str_streams__(streams):
    if isinstance(streams, (list, tuple)):
        s = "[" + "][".join(streams) + "]"
    elif isinstance(streams, str):
        s = f"[{streams}]"
    else:
        raise FilterError(f"Unexpected streams type {str(type(streams))}")
    return s


def wrap_in_streams(filter_list, in_stream, out_stream):
    if isinstance(filter_list, str):
        s = filter_list
    elif isinstance(filter_list, (list, tuple)):
        s = ','.join(filter_list)
    else:
        raise FilterError("Unexpected filter_list type {}".format(type(filter_list)))
    return "[{}]{}[{}]".format(in_stream, s, out_stream)


def in_out(filter_str, in_streams, out_streams):
    return "{}{}{}".format(__str_streams__(in_streams), filter_str, __str_streams__(out_streams))




def zoompan(x_formula, y_formula, z_formula, **kwargs):
    opts = ''
    for k in kwargs:
        opts += ":{}={}".format(k, kwargs[k])
    return f"zoompan=z='{z_formula}':x='{x_formula}':y='{y_formula}'{opts}"

def format(pix_fmts):
    if isinstance(pix_fmts, list):
        s = '|'.join(pix_fmts)
    elif isinstance(pix_fmts, str):
        s = pix_fmts
    else:
        raise FilterError("Unexpected pix_fmts {}".format(pix_fmts))
    return "format=pix_fmts={}".format(s)


def filtercomplex(filter_list):
    if filter_list is None or not filter_list:
        return ''
    sep = " "   # if platform.system() == 'Windows' else " \\\n"
    return '-filter_complex "{}{}"'.format(sep, ('; ' + sep).join(filter_list))


def vfilter(filter_list):
    if filter_list is None or not filter_list:
        return ''
    return '-vf "{}"'.format(','.join(filter_list))


def afilter(filter_list):
    if filter_list is None or not filter_list:
        return ''
    return '-af "{}"'.format(','.join(filter_list))


def inputs_str(input_list):
    sep = " "   # if platform.system() == 'Windows' else " \\\n"
    return sep.join(['-i "{}"'.format(f) for f in input_list])


def format_options(opts):
    if opts is None:
        return ''
    return ' '.join(opts)


def metadata(key, value, track=None, track_type=None):
    if track is None:
        return '-metadata {}="{}"'.format(key, value)
    else:
        if track_type is None:
            track_type = 's:a'
        return '-metadata:{}:{} {}="{}"'.format(track_type, track, key, value)


def vcodec(codec):
    return '-vcodec {}'.format(codec)


def acodec(codec):
    return '-acodec {}'.format(codec)


def disposition(default_track, nb_tracks):
    # -disposition:a:0 default -disposition:a:1
    disp = ''
    for t in range(nb_tracks):
        t_disp = "default" if t == default_track else "none"
        disp += "-disposition:a:{} {} ".format(t, t_disp)
    return disp.rstrip()


def hw_accel_input(**kwargs):
    if kwargs.get('hw_accel', False):
        return '-hwaccel cuvid -c:v h264_cuvid'
    return ''


def hw_accel_output(**kwargs):
    if kwargs.get('hw_accel', False):
        return '-c:v h264_nvenc'
    return ''
