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

"""Named poster templates for printing: a fixed image grid on one of the standard print aspect ratios (4:3, 3:4, 7:5, 5:7),
with a black background, a gutter used both between the images and as the outer margin, and a title stripe at the bottom"""

from __future__ import annotations

from dataclasses import dataclass

import mediatools.imagefile as image

# Fixed look of every template: a black background, a gutter that is both the spacing between images and the outer margin
# (8% of the largest dimension of the top-left image), and a bottom stripe reserved for a title (18% of the grid's height)
BACKGROUND_COLOR: str = "black"
GUTTER: str = "8%"
TITLE_STRIPE: str = "18%"

# Aspect ratios (width / height) accepted for the input images of a template: standard digital photo (4:3), DSLR/35mm landscape
# and portrait (15:10 and 10:15) and widescreen (16:9)
ACCEPTED_IMAGE_RATIOS: tuple[float, ...] = (4 / 3, 15 / 10, 10 / 15, 16 / 9)
# Relative tolerance (to the closest accepted ratio) within which an image's aspect ratio is considered acceptable
RATIO_TOLERANCE: float = 0.02


@dataclass(frozen=True)
class PosterTemplate:
    """A named poster template: a rows x cols grid of images on a page of a given print aspect ratio"""

    rows: int
    cols: int
    page_ratio: str  # The page's aspect ratio (width:height), one of 4:3, 3:4, 7:5, 5:7

    @property
    def image_count(self) -> int:
        """Returns the number of images the template requires"""
        return self.rows * self.cols

    @property
    def layout(self) -> str:
        """Returns the template's grid as the 'RxC' layout expected by the poster tool"""
        return f"{self.rows}x{self.cols}"


# 10 templates: both print formats (4:3/3:4, the "40" family, and 7:5/5:7, the "70" family), both orientations, and a range
# of grid sizes. Names follow <orientation><format>-<rows>x<cols>, eg "landscape40-4x3" (12 images, 4:3) or "portrait70-2x4"
# (8 images, 5:7)
TEMPLATES: dict[str, PosterTemplate] = {
    "landscape40-1x1": PosterTemplate(1, 1, "4:3"),
    "landscape40-2x2": PosterTemplate(2, 2, "4:3"),
    "landscape40-2x3": PosterTemplate(2, 3, "4:3"),
    "landscape40-4x3": PosterTemplate(4, 3, "4:3"),
    "landscape70-1x2": PosterTemplate(1, 2, "7:5"),
    "landscape70-2x3": PosterTemplate(2, 3, "7:5"),
    "portrait40-1x1": PosterTemplate(1, 1, "3:4"),
    "portrait40-2x2": PosterTemplate(2, 2, "3:4"),
    "portrait40-3x2": PosterTemplate(3, 2, "3:4"),
    "portrait70-2x4": PosterTemplate(2, 4, "5:7"),
}


def closest_accepted_ratio(ratio: float) -> float | None:
    """Returns the accepted image ratio closest to a given one, or None if none of them is close enough (see RATIO_TOLERANCE)"""
    best = min(ACCEPTED_IMAGE_RATIOS, key=lambda r: abs(r - ratio))
    return best if abs(best - ratio) / best <= RATIO_TOLERANCE else None


def bad_ratio_images(photos: list[str]) -> list[tuple[str, float]]:
    """Returns the (file, ratio) of the photos whose aspect ratio doesn't match one of ACCEPTED_IMAGE_RATIOS"""
    return [(f, ratio) for f, ratio in ((f, image.ImageFile(f).ratio) for f in photos) if closest_accepted_ratio(ratio) is None]


def defaults(template: PosterTemplate) -> dict:
    """Returns the poster settings a template imposes: its grid layout, and the fixed look common to every template"""
    return {"layout": template.layout, "background_color": BACKGROUND_COLOR, "gutter": GUTTER, "extra_margin_bottom": TITLE_STRIPE}
