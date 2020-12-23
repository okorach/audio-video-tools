import mediatools.utilities as util

class FilterError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message


def __str_streams__(streams):
    if isinstance(streams, list) or isinstance(streams, tuple):
        s = "[" + "][".joint(streams) + "]"
    elif isinstance(streams, str):
        s = "[{}]".format(streams)
    else:
        raise FilterError("Unexpected streams type {}".format(type(streams)))
    return s


def wrap_in_streams(filter_list, in_stream, out_stream):
    if isinstance(filter_list, str):
        s = filter_list
    elif isinstance(filter_list, list) or isinstance(filter_list, tuple):
        s = ','.join(filter_list)
    else:
        raise FilterError("Unexpected filter_list type {}".format(type(filter_list)))
    return "[{}]{}[{}]".format(in_stream, s, out_stream)

def in_out(filter_str, in_streams, out_streams):
    return "{}{}{}".format(__str_streams__(in_streams), filter_str, __str_streams__(out_streams))


def setsar(ratio):
    return "setsar={}".format(ratio)


def zoompan(x_formula, y_formula, z_formula, **kwargs):
    opts = ''
    for k in kwargs:
        opts += ":{}={}".format(k, kwargs[k])
    return "zoompan=z='{}':x='{}':y='{}'{}".format(z_formula, x_formula, y_formula, opts)


def format(pix_fmts):
    if isinstance(pix_fmts, list):
        s = '|'.join(pix_fmts)
    elif isinstance(pix_fmts, str):
        s = pix_fmts
    else:
        raise FilterError("Unexpected pix_fmts {}".format(pix_fmts))
    return "format=pix_fmts={}".format(s)


def fade(direction='in', start=0, duration=0.5, alpha=1):
    return "fade=t={}:st={}:d={}:alpha={}".format(direction, start, duration, alpha)


def fade_in(start=0, duration=0.5, alpha=1):
    return fade('in', start, duration, alpha)


def fade_out(start=0, duration=0.5, alpha=1):
    return fade('out', start, duration, alpha)


def overlay(in_stream_1, in_stream_2, out_stream):
    return "[{}][{}]overlay[{}]".format(in_stream_1, in_stream_2, out_stream)


def trim(duration=None, start=None, stop=None):
    if duration is None and (start is None or stop is None):
        raise FilterError("No duration, start or stop for trim filter")
    s = 'trim='
    if duration is not None:
        s += 'duration={}'.format(duration)
    if start is not None:
        s += 'start={}'.format(start)
    if stop is not None:
        s += 'stop={}'.format(stop)
    return s


def setpts(pts_formula):
    return "setpts={}".format(pts_formula)


def scale(x, y):
    return "scale={}:{}".format(x, y)


def crop(x, y, x_formula=None, y_formula=None):
    s = "crop={}:{}".format(x, y)
    if x_formula is not None:
        s += ':' + str(x_formula)
    if y_formula is not None:
        s += ':' + str(y_formula)
    return s
