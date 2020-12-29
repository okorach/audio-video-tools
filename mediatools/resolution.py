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

import re


class Resolution:
    RES_8K = "7680x4320"
    RES_4K = "3840x2160"
    RES_1080P = "1920x1080"
    RES_720P = "1280x720"
    RES_HD = RES_1080P
    RES_540P = "960x540"
    RES_400P = "720x400"
    RES_360P = "640x360"
    RES_VGA = "640x480"
    RES_XGA = "1024x768"

    DEFAULT_VIDEO = RES_4K

    RATIO_16_9 = 16 / 9
    RATIO_15_10 = 15 / 10
    RATIO_4_3 = 4 / 3

    def __init__(self, **kwargs):
        self.width = 0
        self.height = 0
        self.pixels = 0
        self.ratio = None
        if 'width' in kwargs and 'height' in kwargs:
            w = kwargs['width']
            h = kwargs['height']
        elif 'resolution' in kwargs:
            r = kwargs['resolution']
            if re.search('x', r):
                (w, h) = r.split('x', maxsplit=2)
            elif re.search(':', r):
                (w, h) = r.split(':', maxsplit=2)
        self.width = int(w)
        self.height = int(h)
        self.ratio = self.width / self.height
        self.pixels = self.width * self.height

    def is_ratio(self, ratio):
        return abs(ratio - self.ratio) < 0.02

    def calc_resolution(self, width, height, orientation='landscape'):
        iw, ih = self.width, self.height
        if orientation == 'portrait':
            width, height = height, width
            iw, ih = ih, iw
        a = str(width).split('%')
        w = int(width) if len(a) == 1 else int(iw * int(a[0]) / 100)
        a = str(height).split('%')
        h = int(height) if len(a) == 1 else int(ih * int(a[0]) / 100)
        return (w, h)

    def __str__(self):
        return self.as_string('x')

    def as_string(self, separator="x"):
        return "{}{}{}".format(self.width, separator, self.height)

    def as_list(self):
        return [self.width, self.height]

    def as_tuple(self):
        return (self.width, self.height)


RES_VIDEO_DEFAULT = Resolution(resolution=Resolution.DEFAULT_VIDEO)
RES_VIDEO_4K = Resolution(resolution=Resolution.RES_4K)
