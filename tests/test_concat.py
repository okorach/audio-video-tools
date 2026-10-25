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

import os
import sys
from pathlib import Path
from unittest.mock import patch

import mediatools.utilities as util
import mediatools.videofile as video
from mediatools import tools
import pytest

VIDEO1 = "it" + os.sep + "video-720p.mp4"
VIDEO2 = "it" + os.sep + "video-720p.mp4"
TMP1 = util.get_tmp_file() + ".mp4"
TMP2 = util.get_tmp_file() + ".mp4"
TMP3 = util.get_tmp_file() + ".mp4"


def test_main_with_output(short_video: str, tmp_path: Path) -> None:
    """Main with output"""
    util.HW_ACCEL = False
    output = str(tmp_path / "concat.mp4")
    with patch.object(sys, "argv", ["videotool", "concat", "-g", "3", "-i", short_video, short_video, "-o", output]):
        try:
            tools.videotool()
        except SystemExit as e:
            assert int(str(e)) == 0
    assert abs(2 * video.VideoFile(short_video).duration - video.VideoFile(output).duration) < 0.1


def test_main_help() -> None:
    """Main help"""
    with patch.object(sys, "argv", ["videotool", "concat", "-h"]):
        try:
            tools.videotool()
            pytest.fail("An exception was expected")
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_bad_option() -> None:
    """Main bad option"""
    with patch.object(sys, "argv", ["videotool", "concat", "-i", VIDEO1, "--badoption", "yes"]):
        try:
            tools.videotool()
            pytest.fail("An exception was expected")
        except SystemExit as e:
            assert int(str(e)) == 2


def test_main_no_file() -> None:
    """Main no file"""
    with patch.object(sys, "argv", ["videotool", "concat", "-o", TMP1]):
        try:
            tools.videotool()
            pytest.fail("An exception was expected")
        except SystemExit as e:
            assert int(str(e)) == 2
