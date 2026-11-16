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

"""Tests of the named poster templates"""

import os

import pytest

import mediatools.poster_templates as templates

DIR = "it" + os.sep
IMG_4X3 = DIR + "img-640x480.jpg"  # 640x480, exactly 4:3
IMG_16X9 = DIR + "img-3000x1682.jpg"  # 3000x1682, ~16:9
IMG_UNSUPPORTED = DIR + "img-2320x4000.jpg"  # 2320x4000, ratio 0.58 - not one of the accepted ratios


def test_exactly_10_templates() -> None:
    """There are exactly 10 named templates"""
    assert len(templates.TEMPLATES) == 10


def test_template_names_follow_the_naming_convention() -> None:
    """Every template name is <orientation><format>-<rows>x<cols>, matching its own grid"""
    for name, template in templates.TEMPLATES.items():
        orientation, _, grid = name.partition("-")
        assert orientation.startswith(("landscape", "portrait"))
        assert grid == f"{template.rows}x{template.cols}"


def test_template_page_ratios_are_print_ratios() -> None:
    """Every template's page ratio is one of the 4 standard print ratios"""
    for template in templates.TEMPLATES.values():
        assert template.page_ratio in ("4:3", "3:4", "7:5", "5:7")


def test_examples_from_the_request() -> None:
    """The 2 templates explicitly named in the request exist, with the expected grid"""
    assert templates.TEMPLATES["landscape40-4x3"].rows == 4
    assert templates.TEMPLATES["landscape40-4x3"].cols == 3
    assert templates.TEMPLATES["portrait70-2x4"].rows == 2
    assert templates.TEMPLATES["portrait70-2x4"].cols == 4


def test_image_count_and_layout() -> None:
    """image_count is rows * cols, layout is the 'RxC' string expected by the poster tool"""
    template = templates.PosterTemplate(2, 3, "4:3")
    assert template.image_count == 6
    assert template.layout == "2x3"


def test_closest_accepted_ratio() -> None:
    """The accepted ratio closest to a given one is returned, None when none is close enough"""
    assert templates.closest_accepted_ratio(4 / 3) == pytest.approx(4 / 3)
    assert templates.closest_accepted_ratio(15 / 10) == pytest.approx(15 / 10)
    assert templates.closest_accepted_ratio(10 / 15) == pytest.approx(10 / 15)
    assert templates.closest_accepted_ratio(16 / 9) == pytest.approx(16 / 9)
    assert templates.closest_accepted_ratio(1.0) is None  # a square image matches none of them


def test_bad_ratio_images() -> None:
    """bad_ratio_images returns only the images whose ratio doesn't match an accepted one"""
    bad = templates.bad_ratio_images([IMG_4X3, IMG_16X9, IMG_UNSUPPORTED])
    assert [os.path.basename(f) for f, _ in bad] == [os.path.basename(IMG_UNSUPPORTED)]


def test_bad_ratio_images_empty_when_all_accepted() -> None:
    """No image is reported when they all match an accepted ratio"""
    assert templates.bad_ratio_images([IMG_4X3, IMG_16X9]) == []


def test_defaults() -> None:
    """defaults() returns the fixed settings a template imposes: its layout, black background, 8% gutter and 18% title stripe"""
    template = templates.PosterTemplate(2, 3, "4:3")
    assert templates.defaults(template) == {
        "layout": "2x3",
        "background_color": "black",
        "gutter": "8%",
        "extra_margin_bottom": "18%",
    }
