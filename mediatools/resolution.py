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
#

import re
from typing import ClassVar
import mediatools.options as opt
import mediatools.exceptions as ex


def canonical(res: str) -> str:
    """Returns the WxH resolution of an alias (case insensitive), see Resolution.ALIASES. Other values are returned unchanged"""
    if isinstance(res, str):
        return Resolution.ALIASES.get(res.strip().lower(), res)
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

    RES_2_5K: str = "2560x1440"
    RES_2_7K: str = "2704x1520"

    DEFAULT_VIDEO: str = RES_4K

    # Aliases of the resolutions, in lower case: the aliases are case insensitive
    ALIASES: ClassVar[dict[str, str]] = {
        "4k": RES_4K,
        "2160p": RES_4K,
        "2.5k": RES_2_5K,
        "1440p": RES_2_5K,
        "2.7k": RES_2_7K,
        "1520p": RES_2_7K,
        "fhd": RES_1080P,
        "1080p": RES_1080P,
        "hd": RES_720P,
        "720p": RES_720P,
        "540p": RES_540P,
        "400p": RES_400P,
        "360p": RES_360P,
        "vga": RES_VGA,
        "xga": RES_XGA,
    }

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
            r = canonical(kwargs.get("resolution", kwargs.get(opt.Option.RESOLUTION)))
            if re.search(r"[x:]", r):
                w, h = re.split(r"[x:]", r, maxsplit=2)
        if int(w) <= 0 or int(h) <= 0:
            raise ex.DimensionError("width and height must be strictly positive")
        self.width = int(w)
        self.height = int(h)
        self.ratio = self.width / self.height
        self.pixels = self.width * self.height

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"

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
        return f"{self.width}{separator}{self.height}"

    def as_list(self) -> list[int]:
        return [self.width, self.height]

    def as_tuple(self) -> tuple[int, int]:
        return (self.width, self.height)


RES_VIDEO_DEFAULT: Resolution = Resolution(resolution=Resolution.DEFAULT_VIDEO)
RES_VIDEO_4K: Resolution = Resolution(resolution=Resolution.RES_4K)
