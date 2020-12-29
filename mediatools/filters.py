#!python3
#
# media-tools
# Copyright (C) 2019-2020 Olivier Korach
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

import platform

class FilterError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message


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


def overlay(in_stream_1, in_stream_2, out_stream, x=0, y=0):
    return "[{}][{}]overlay={}:{}[{}]".format(in_stream_1, in_stream_2, x, y, out_stream)


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


def deshake(x=-1, y=-1, w=-1, h=-1, rx=64, ry=64):
    return "deshake=x={}:y={}:w={}:h={}:rx={}:ry={}".format(x, y, w, h, rx, ry)


def filtercomplex(filter_list):
    sep = " "   # if platform.system() == 'Windows' else " \\\n"
    return '-filter_complex "{}{}"'.format(sep, ('; ' + sep).join(filter_list))


def vfilter(filter_list):
    return '-vf "{}"'.format(','.join(filter_list))


def inputs_str(input_list):
    sep = " "   # if platform.system() == 'Windows' else " \\\n"
    return sep.join(['-i "{}"'.format(f) for f in input_list])


def hw_accel_input(**kwargs):
    if kwargs.get('hw_accel', False):
        return '-hwaccel cuvid -c:v h264_cuvid'
    return ''


def hw_accel_output(**kwargs):
    if kwargs.get('hw_accel', False):
        return '-c:v h264_nvenc'
    return ''
