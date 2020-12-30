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

'''
This file encapsulates
- various constants
- data structures and
- translation functions
used in several places
in mediatools library
'''


class OptionFfmpeg:
    '''Documents supported ffmpeg options'''
    FORMAT = 'f'
    SIZE = 's'
    VCODEC = 'vcodec'
    VCODEC2 = 'c:v'
    VCODEC3 = 'codec:v'
    ACODEC = 'acodec'
    ACODEC2 = 'c:a'
    ACODEC3 = 'codec:a'
    VBITRATE = 'b:v'
    ABITRATE = 'b:a'
    SIZE = 's'
    FPS = 'r'
    ASPECT = 'aspect'
    DEINTERLACE = 'deinterlace'
    ACHANNEL = 'ac'
    VFILTER = 'vf'
    START = 'ss'
    STOP = 'to'


class Option:
    '''Documents supported audio-video-tools encoding options'''
    FORMAT = 'format'
    SIZE = 'size'
    VCODEC = 'vcodec'
    ACODEC = 'acodec'
    VBITRATE = 'vbitrate'
    ABITRATE = 'abitrate'
    WIDTH = 'width'
    HEIGHT = 'height'
    FPS = 'fps'
    ASPECT = 'aspect'
    DEINTERLACE = 'deinterlace'
    ACHANNEL = 'achannels'
    VFILTER = 'vfilter'
    START = 'start'
    STOP = 'stop'
    ASAMPLING = 'asamplerate'
    AUTHOR = 'author'
    TITLE = 'title'
    ALBUM = 'album'
    YEAR = 'year'
    TRACK = 'track'
    GENRE = 'genre'
    DURATION = 'duration'
    LANGUAGE = 'language'


M2F_MAPPING = {
    Option.FORMAT: OptionFfmpeg.FORMAT,
    Option.VCODEC: OptionFfmpeg.VCODEC,
    Option.VBITRATE: OptionFfmpeg.VBITRATE,
    Option.ACODEC: OptionFfmpeg.ACODEC,
    Option.ABITRATE: OptionFfmpeg.ABITRATE,
    Option.FPS: OptionFfmpeg.FPS,
    Option.ASPECT: OptionFfmpeg.ASPECT,
    Option.SIZE: OptionFfmpeg.SIZE,
    Option.DEINTERLACE: OptionFfmpeg.DEINTERLACE,
    Option.ACHANNEL: OptionFfmpeg.ACHANNEL,
    Option.VFILTER: OptionFfmpeg.VFILTER,
    Option.START: OptionFfmpeg.START,
    Option.STOP: OptionFfmpeg.STOP
}

F2M_MAPPING = {}
for k, v in M2F_MAPPING.items():
    F2M_MAPPING[v] = k
F2M_MAPPING[OptionFfmpeg.ACODEC2] = Option.ACODEC
F2M_MAPPING[OptionFfmpeg.ACODEC3] = Option.ACODEC
F2M_MAPPING[OptionFfmpeg.VCODEC2] = Option.VCODEC
F2M_MAPPING[OptionFfmpeg.VCODEC3] = Option.VCODEC


def media2ffmpeg(options):
    # Returns ffmpeg cmd options dict from media options dict
    import mediatools.utilities as util
    if options is None:
        return {}
    ffopts = {}
    for key in M2F_MAPPING:
        if key in options and options[key] is not None:
            ffopts[M2F_MAPPING[key]] = options[key]
    return util.remove_nones(ffopts)


def ffmpeg2media(options):
    # Returns ffmpeg cmd options dict from media options dict
    import mediatools.utilities as util
    if options is None:
        return {}
    mopts = {}
    for key in M2F_MAPPING:
        if key in options and options[key] is not None:
            mopts[M2F_MAPPING[key]] = options[key]
    return util.remove_nones(mopts)
