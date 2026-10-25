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

import pytest
import mediatools.resolution as res
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.exceptions as ex


@pytest.mark.parametrize("alias,expected", [("720p", "1280x720"), ("1080p", "1920x1080"), ("4k", "3840x2160")])
def test_canonical(alias: str, expected: str) -> None:
    """Canonical"""
    assert res.canonical(alias) == expected


def test_multiply() -> None:
    """Multiply"""
    x, y = 1000, 200
    r = res.Resolution(width=x, height=y)
    r2 = r * 2
    assert r2.width == x * 2
    assert r2.height == y * 2


def test_multiply_by_0() -> None:
    """Multiply by 0"""
    r = res.Resolution(width=300, height=17)
    try:
        _ = r * 0
    except ex.DimensionError as e:
        assert e.message == "width and height must be strictly positive"


def test_multiply_by_negative() -> None:
    """Multiply by negative"""
    r = res.Resolution(width=100, height=100)
    try:
        _ = r * -1
    except ex.DimensionError as e:
        assert e.message == "width and height must be strictly positive"


@pytest.mark.parametrize(
    "alias,expected",
    [
        ("4k", "3840x2160"),
        ("4K", "3840x2160"),
        ("2160p", "3840x2160"),
        ("2.7k", "2704x1520"),
        ("2.7K", "2704x1520"),
        ("1520p", "2704x1520"),
        ("fhd", "1920x1080"),
        ("FHD", "1920x1080"),
        ("Fhd", "1920x1080"),
        ("1080p", "1920x1080"),
        ("hd", "1280x720"),
        ("HD", "1280x720"),
        ("720p", "1280x720"),
        ("2.5k", "2560x1440"),
        ("2.5K", "2560x1440"),
        ("1440p", "2560x1440"),
        ("VGA", "640x480"),
        (" 4k ", "3840x2160"),
    ],
)
def test_aliases(alias: str, expected: str) -> None:
    """Aliases"""
    assert res.canonical(alias) == expected
    assert str(res.Resolution(resolution=alias)) == expected


def test_not_an_alias() -> None:
    """Not an alias"""
    assert res.canonical("1280x720") == "1280x720"
    assert res.canonical("unknown") == "unknown"
    assert res.canonical(None) is None


@pytest.mark.parametrize("alias,expected", [("4K", "3840x2160"), ("2.7k", "2704x1520"), ("FHD", "1920x1080"), ("720P", "1280x720")])
def test_resolution_option_aliases(alias: str, expected: str) -> None:
    """Resolution option aliases"""
    parser = util.get_common_args("test-resolution", "test")
    assert util.parse_media_args(parser, ["-i", "it/song.mp3", "--resolution", alias])["resolution"] == expected
    assert util.parse_media_args(parser, ["-i", "it/song.mp3", "-s", alias])["resolution"] == expected
    assert util.parse_media_args(parser, ["-i", "it/song.mp3", "-s", "640x360"])["resolution"] == "640x360"
    assert "resolution" not in util.parse_media_args(parser, ["-i", "it/song.mp3"])


@pytest.mark.parametrize(
    "alias,expected", [("2.7k", ("2704", "1520")), ("4K", ("3840", "2160")), ("1k", ("1920", "1080")), ("1280x720", ("1280", "720"))]
)
def test_crop_box_aliases(alias: str, expected: tuple) -> None:
    """Crop box aliases"""
    assert video.parse_crop_box(alias) == expected
