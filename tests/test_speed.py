#!python3
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
from mediatools import speed
import mediatools.utilities as util
import mediatools.videofile as video

CMD = "video-speed"
VIDEO = "it" + os.sep + "video-360p-1.mp4"
TMP1 = util.get_tmp_file() + ".mp4"


def test_main():
    with patch.object(sys, "argv", [CMD, "-p", "360p", "-i", VIDEO, "--speed", "2"]):
        speed.main()
        assert True


def test_main_with_output():
    with patch.object(sys, "argv", [CMD, "-p", "360p", "-i", VIDEO, "-o", TMP1, "--speed", "200%"]):
        speed.main()
        assert abs(video.VideoFile(VIDEO).duration - 2 * video.VideoFile(TMP1).duration) < 0.06
        assert video.VideoFile(TMP1).audio_codec is None
        os.remove(TMP1)


def test_slowmo():
    with patch.object(sys, "argv", [CMD, "-p", "360p", "-i", VIDEO, "-o", TMP1, "--speed", "50%"]):
        speed.main()
        assert abs(video.VideoFile(VIDEO).duration - 0.5 * video.VideoFile(TMP1).duration) < 0.06
        assert video.VideoFile(TMP1).audio_codec is None
        os.remove(TMP1)


def test_keep_audio():
    with patch.object(sys, "argv", [CMD, "-p", "360p", "-i", VIDEO, "-o", TMP1, "-k", "--speed", "4"]):
        speed.main()
        # TODO - Truncate audio when video is shorter, and adjust tests
        assert abs(video.VideoFile(VIDEO).duration - 4 * video.VideoFile(TMP1).duration) < 0.06
        assert video.VideoFile(TMP1).audio_codec == "aac"
        os.remove(TMP1)


def test_main_help():
    with patch.object(sys, "argv", [CMD, "-h"]):
        try:
            speed.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_bad_option():
    with patch.object(sys, "argv", [CMD, "-i", VIDEO, "--badoption", "yes"]):
        try:
            speed.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2


def test_main_no_file():
    with patch.object(sys, "argv", [CMD, "-o", TMP1]):
        try:
            speed.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2


def test_bad_speed():
    with patch.object(sys, "argv", [CMD, "-i", VIDEO, "--speed", "212%"]):
        try:
            speed.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 1
