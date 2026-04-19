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

import re
import mediatools.options as opt
import mediatools.exceptions as ex


def canonical(res: str) -> str:
    if res == "720p":
        res = Resolution.RES_720P
    elif res == "540p":
        res = Resolution.RES_540P
    elif res == "400p":
        res = Resolution.RES_400P
    elif res in ("vga", "VGA"):
        res = Resolution.RES_VGA
    elif res in ("xga", "XGA"):
        res = Resolution.RES_XGA
    elif res == "1080p":
        res = Resolution.RES_1080P
    elif res in ("4k", "4K", "2160p"):
        res = Resolution.RES_4K
    return res


class Resolution:
    RES_8K: str = "7680x4320"
    RES_4K: str = "3840x2160"
    RES_1080P: str = "1920x1080"
    RES_720P: str = "1280x720"
    RES_HD: str = RES_1080P
    RES_540P: str = "960x540"
    RES_400P: str = "720x400"
    RES_360P: str = "640x360"
    RES_VGA: str = "640x480"
    RES_XGA: str = "1024x768"

    DEFAULT_VIDEO: str = RES_4K

    RATIO_16_9: float = 16 / 9
    RATIO_15_10: float = 15 / 10
    RATIO_4_3: float = 4 / 3

    def __init__(self, **kwargs) -> None:
        self.width: int = 0
        self.height: int = 0
        self.pixels: int = 0
        self.ratio: float | None = None
        if "width" in kwargs and "height" in kwargs:
            w = kwargs["width"]
            h = kwargs["height"]
        elif "resolution" in kwargs or opt.Option.RESOLUTION in kwargs:
            r = canonical(kwargs.get("resolution", kwargs.get(opt.Option.RESOLUTION, None)))
            if re.search(r"[x:]", r):
                (w, h) = re.split(r"[x:]", r, maxsplit=2)
        if int(w) <= 0 or int(h) <= 0:
            raise ex.DimensionError("width and height must be strictly positive")
        self.width = int(w)
        self.height = int(h)
        self.ratio = self.width / self.height
        self.pixels = self.width * self.height

    def __str__(self) -> str:
        return "{}x{}".format(self.width, self.height)

    def __mul__(self, factor: float) -> "Resolution":
        return Resolution(width=self.width * factor, height=self.height * factor)

    # def __str__(self):
    #     return str(vars(self))

    def is_ratio(self, ratio: float) -> bool:
        return abs(ratio - self.ratio) < 0.02

    def calc_resolution(self, width: int | str, height: int | str, orientation: str = "landscape") -> tuple[int, int]:
        iw, ih = self.width, self.height
        if orientation == "portrait":
            width, height = height, width
            iw, ih = ih, iw
        a = str(width).split("%")
        w = int(width) if len(a) == 1 else int(iw * int(a[0]) / 100)
        a = str(height).split("%")
        h = int(height) if len(a) == 1 else int(ih * int(a[0]) / 100)
        return (w, h)

    def as_string(self, separator: str = "x") -> str:
        return "{}{}{}".format(self.width, separator, self.height)

    def as_list(self) -> list[int]:
        return [self.width, self.height]

    def as_tuple(self) -> tuple[int, int]:
        return (self.width, self.height)


RES_VIDEO_DEFAULT: Resolution = Resolution(resolution=Resolution.DEFAULT_VIDEO)
RES_VIDEO_4K: Resolution = Resolution(resolution=Resolution.RES_4K)
