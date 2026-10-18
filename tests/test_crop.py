#
# media-tools
# Copyright (C) 2019-2025 Olivier Korach
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

"""Tests of the media-crop CLI"""

import os
import sys
from unittest import mock

import pytest

from mediatools import crop

FILE = "it" + os.sep + "video-720p.mp4"


def _run(*args: str) -> mock.Mock:
    """Runs media-crop with a mocked VideoFile, returns the mocked crop method"""
    video = mock.Mock()
    video.crop.return_value = "out.mp4"
    with mock.patch.object(sys, "argv", ["media-crop", "-i", FILE, *args]), mock.patch("mediatools.creator.file", return_value=video):
        crop.main()
    return video.crop


def test_default_position_and_box() -> None:
    """No option means a centered 1920x1080 crop"""
    kwargs = _run().call_args.kwargs
    assert kwargs["position"] == "center"
    assert (kwargs["width"], kwargs["height"]) == ("1920", "1080")


def test_position_combination() -> None:
    """--top --left is passed as a top left position"""
    kwargs = _run("--box", "1280x720", "--top", "--left").call_args.kwargs
    assert kwargs["position"] == "top left"
    assert (kwargs["width"], kwargs["height"]) == ("1280", "720")


def test_bottom_center() -> None:
    """--bottom --center is accepted"""
    kwargs = _run("--box", "720x1280", "--bottom", "--center").call_args.kwargs
    assert "bottom" in kwargs["position"]
    assert (kwargs["width"], kwargs["height"]) == ("720", "1280")


@pytest.mark.parametrize(
    ("option", "position"),
    [("--topleft", "top left"), ("--topright", "top right"), ("--bottomleft", "bottom left"), ("--bottomright", "bottom right")],
)
def test_corner_shortcuts(option: str, position: str) -> None:
    """--topleft etc. are equivalent to the 2 options they combine"""
    assert _run(option).call_args.kwargs["position"] == position
    vertical, horizontal = position.split()
    assert _run(f"--{vertical}", f"--{horizontal}").call_args.kwargs["position"] == position


def test_corner_conflict() -> None:
    """A corner shortcut conflicting with another position exits with code 2"""
    with pytest.raises(SystemExit) as e:
        _run("--topleft", "--bottom")
    assert e.value.code == 2


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        ("4k", ("3840", "2160")),
        ("4K", ("3840", "2160")),
        ("fhd", ("1920", "1080")),
        ("FHD", ("1920", "1080")),
        ("1k", ("1920", "1080")),
        ("1K", ("1920", "1080")),
        ("hd", ("1280", "720")),
        ("HD", ("1280", "720")),
        ("1280X720", ("1280", "720")),
    ],
)
def test_box_aliases(box: str, expected: tuple) -> None:
    """--box accepts size aliases, case insensitive"""
    kwargs = _run("--box", box).call_args.kwargs
    assert (kwargs["width"], kwargs["height"]) == expected


@pytest.mark.parametrize("args", [["--top", "--bottom"], ["--left", "--right"], ["--box", "1280"], ["--box", "8k"], ["--box", "axb"]])
def test_invalid_options(args: list) -> None:
    """Incompatible positions and malformed box exit with code 2"""
    with pytest.raises(SystemExit) as e:
        _run(*args)
    assert e.value.code == 2


def test_box_too_big() -> None:
    """A crop box bigger than the source fails with a non 0 exit code"""
    with mock.patch.object(sys, "argv", ["media-crop", "-i", FILE, "--box", "4000x3000", "--hw_accel", "off"]), pytest.raises(SystemExit) as e:
        crop.main()
    assert e.value.code == 1
