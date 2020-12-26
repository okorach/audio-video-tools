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

import mediatools.options as opt


LANGUAGE_MAPPING = {'fre': 'French', 'eng': 'English'}


class Encoder:
    '''Encoder abstraction'''
    SETTINGS = ['format', 'vcodec', 'vbitrate', 'acodec', 'abitrate', 'fps', 'aspect',
                'vsize', 'deinterlace', 'achannel', 'asample', 'vfilter', 'start', 'stop']

    def __init__(self, **kwargs):
        self.format = None
        self.aspect = None
        self.size = None
        self.vcodec = 'copy'
        self.vbitrate = None
        self.video_fps = None
        self.abitrate = None
        self.acodec = 'copy'
        self.audio_language = None
        self.audio_sample_rate = None
        self.start = None
        self.stop = None
        self.vfilters = []
        self.add_settings(**kwargs)
        self.others = {}

    def add_settings(self, **kwargs):
        kwsettings = {}
        for k in kwargs:
            if k in Encoder.SETTINGS and kwargs[k] is not None:
                kwsettings[k] = kwargs[k]
        if 'vcodec' in kwsettings:
            self.vcodec = kwsettings[opt.media.VCODEC]
        if 'vbitrate' in kwsettings:
            self.vbitrate = kwsettings[opt.media.VBITRATE]
        if 'acodec' in kwsettings:
            self.acodec = kwsettings[opt.media.ACODEC]
        if 'abitrate' in kwsettings:
            self.abitrate = kwsettings[opt.media.ABITRATE]
        if 'aspect' in kwsettings:
            self.aspect = kwsettings[opt.media.ASPECT]
        if 'size' in kwsettings:
            self.size = kwsettings[opt.media.SIZE]
        if 'start' in kwsettings:
            self.start = kwsettings[opt.media.START]
        if 'stop' in kwsettings:
            self.start = kwsettings[opt.media.STOP]
        if 'format' in kwsettings:
            self.format = kwsettings[opt.media.FORMAT]

    def set_format(self, fmt):
        self.format = fmt

    def add_vfilter(self, vfilter):
        self.vfilters.append(vfilter)

    def get_vfilters_string(self):
        cmd = ''
        for f in self.vfilters:
            cmd = cmd + '-filter:v "%s" ' % f
        return cmd.strip()

    def add_crop_filter(self, width, height, top, left):
        self.add_vfilter("crop={0}:{1}:{2}:{3}".format(width, height, top, left))

    def add_deshake_filter(self, width, height):
        # ffmpeg -i <in> -f mp4 -vf deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=16 -b:v 2048k <out>
        self.add_vfilter("deshake=x=-1:y=-1:w=-1:h=-1:rx={0}:ry={1}".format(width, height))

    def add_fade_filter(self, fade_d, start=None, stop=None):
        if start is None:
            start = self.start
        if start is None:
            start = 0
        if stop is None:
            stop = self.stop
        fmt = "fade=type={0}:duration={1}:start_time={2}"
        fader = fmt.format('in', fade_d, start) + "," + fmt.format('out', fade_d, stop - fade_d)
        self.add_vfilter(fader)

    def ffmpeg_opts(self):
        '''Builds string corresponding to ffmpeg conventions'''
        options = vars(self)
        cmd = ''
        for option in options.keys():
            if options[option] is not None and not isinstance(options[option], list):
                cmd = cmd + " -{0} {1}".format(opt.M2F_MAPPING[option], options[option])
        cmd = cmd + ' ' + self.get_vfilters_string()
        return cmd.strip()
