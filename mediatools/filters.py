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

import mediatools.utilities as util
import mediatools.exceptions as ex

ROTATION_VALUES = ('clock', 'cclock', 'clock_flip', 'cclock_flip')

ERR_ROTATION_ARG_1 = 'rotation must be one of {}'.format(', '.join(ROTATION_VALUES))
ERR_ROTATION_ARG_2 = 'rotation must be between 0 and 7'
ERR_ROTATION_ARG_3 = 'incorrect value for rotation'

class FilterError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message


VIDEO_TYPE = 0
AUDIO_TYPE = 1


class Simple:
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
        if len(self.filters) == 0:
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


class Complex:
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
        util.logger.debug('Adding filtergraph %s, %s, %s', str(inputs), str(simple_filter), outs)
        self.filtergraph.append((inputs, simple_filter, outs))
        return outs


def __str_streams__(streams):
    if isinstance(streams, (list, tuple)):
        s = "[" + "][".join(streams) + "]"
    elif isinstance(streams, str):
        s = "[{}]".format(streams)
    else:
        raise FilterError("Unexpected streams type {}".format(type(streams)))
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


def setsar(ratio):
    ratio = '/'.join(ratio.split(':'))
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


def overlay(x=0, y=0):
    return "overlay={}:{}".format(int(x), int(y))


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
    return "scale={}:{}".format(int(x), int(y))


def crop(x, y, x_formula=None, y_formula=None):
    s = "crop={}:{}".format(x, y)
    if x_formula is not None:
        s += ':' + str(x_formula)
    if y_formula is not None:
        s += ':' + str(y_formula)
    return s


def deshake(x=-1, y=-1, w=-1, h=-1, rx=64, ry=64):
    return "deshake=x={}:y={}:w={}:h={}:rx={}:ry={}".format(x, y, w, h, rx, ry)


def reverse():
    return "reverse"


def areverse():
    return "areverse"


def volume(vol):
    ''' Sets video / audio volume
    Can pass vol as a multiplier of current volume or absolute value like -6.0dB '''
    return "volume={}".format(vol)


def rotate(rotation=90):
    if isinstance(rotation, str) and rotation not in ROTATION_VALUES:
        raise ex.InputError(ERR_ROTATION_ARG_1, 'rotate')
    if not isinstance(rotation, int):
        raise ex.InputError(ERR_ROTATION_ARG_3, 'rotate')
    rotation = int(rotation)
    if rotation == 90:
        rotation = 1
    if rotation == -90:
        rotation = 2
    if rotation < 0 or rotation > 7:
        raise ex.InputError(ERR_ROTATION_ARG_2, 'rotate')
    return "transpose={}".format(rotation)

def speed(target_speed):
    s = util.percent_or_absolute(target_speed)
    if s > 1:
        return select('not(mod(n,{}))'.format(s)) + ',' + setpts('N/FRAME_RATE/TB')
    else:
        return setpts("{}*PTS".format(1 / float(s)))


def select(expr):
    return "select='{}'".format(expr)


def filtercomplex(filter_list):
    if filter_list is None or len(filter_list) == 0:
        return ''
    sep = " "   # if platform.system() == 'Windows' else " \\\n"
    return '-filter_complex "{}{}"'.format(sep, ('; ' + sep).join(filter_list))


def vfilter(filter_list):
    if filter_list is None or len(filter_list) == 0:
        return ''
    return '-vf "{}"'.format(','.join(filter_list))


def afilter(filter_list):
    if filter_list is None or len(filter_list) == 0:
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
