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


@pytest.mark.parametrize("args", [["--top", "--bottom"], ["--left", "--right"], ["--box", "1280"]])
def test_invalid_options(args: list) -> None:
    """Incompatible positions and malformed box exit with code 2"""
    with pytest.raises(SystemExit) as e:
        _run(*args)
    assert e.value.code == 2  # noqa: PLR2004


def test_box_too_big() -> None:
    """A crop box bigger than the source fails with a non 0 exit code"""
    with mock.patch.object(sys, "argv", ["media-crop", "-i", FILE, "--box", "4000x3000", "--hw_accel", "off"]), pytest.raises(SystemExit) as e:
        crop.main()
    assert e.value.code == 1
