#
# media-tools
# Copyright (C) 2021 Olivier Korach
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
from unittest.mock import patch
from mediatools import tools
import mediatools.utilities as util
import mediatools.videofile as video

VIDEO = "it" + os.sep + "video-720p.mp4"
AUDIO1 = "it" + os.sep + "seal.mp3"
AUDIO2 = "it" + os.sep + "ub40.mp3"
TMP1 = util.get_tmp_file() + ".mp4"


def test_main() -> None:
    """Main"""
    with patch.object(sys, "argv", ["videotool", "mux", "-g", "2", "-i", VIDEO, AUDIO1, AUDIO2]):
        try:
            tools.videotool()
            assert True
        except SystemExit as e:
            assert int(str(e)) == 0
            v = video.VideoFile(TMP1)
            v.get_specs()
            assert v.duration > 0


def test_main_with_output() -> None:
    """Main with output"""
    with patch.object(sys, "argv", ["videotool", "mux", "-g", "2", "-i", AUDIO1, VIDEO, AUDIO2, "-o", TMP1]):
        try:
            tools.videotool()
            v = video.VideoFile(TMP1)
            v.get_specs()
            assert v.duration > 0
            os.remove(TMP1)
        except SystemExit as e:
            assert int(str(e)) == 0
            v = video.VideoFile(TMP1)
            v.get_specs()
            assert v.duration > 0
            os.remove(TMP1)


def test_main_help() -> None:
    """Main help"""
    with patch.object(sys, "argv", ["videotool", "mux", "-b", "black", "-m", "10", "--stretch", "-h"]):
        try:
            tools.videotool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_bad_option() -> None:
    """Main bad option"""
    with patch.object(sys, "argv", ["videotool", "mux", "-b", "black", "-m", "10", "--stretch", "--badoption", "yes"]):
        try:
            tools.videotool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2


def test_main_no_file() -> None:
    """Main no file"""
    with patch.object(sys, "argv", ["videotool", "mux", "-g", "4", "-b", "black", "-m", "10"]):
        try:
            tools.videotool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2
