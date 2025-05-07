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
from mediatools import reverse
import mediatools.utilities as util
import mediatools.videofile as video

CMD = "video-reverse"
VIDEO = "it" + os.sep + "video-360p-1.mp4"
TMP1 = util.get_tmp_file() + ".mp4"


def test_main():
    with patch.object(sys, "argv", [CMD, "-g", "2", "-i", VIDEO]):
        try:
            reverse.main()
            assert True
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_with_output():
    with patch.object(sys, "argv", [CMD, "-g", "2", "-i", VIDEO, "-o", TMP1]):
        try:
            reverse.main()
            assert abs(video.VideoFile(VIDEO).duration - video.VideoFile(TMP1).duration) < 0.06
            assert video.VideoFile(TMP1).audio_codec is None
            os.remove(TMP1)
        except SystemExit as e:
            assert int(str(e)) == 0
            assert abs(video.VideoFile(VIDEO).duration - video.VideoFile(TMP1).duration) < 0.06
            assert video.VideoFile(TMP1).audio_codec is None
            os.remove(TMP1)


def test_keep_audio():
    with patch.object(sys, "argv", [CMD, "-g", "2", "-i", VIDEO, "-o", TMP1, "-k"]):
        try:
            reverse.main()
            assert abs(video.VideoFile(VIDEO).duration - video.VideoFile(TMP1).duration) < 0.06
            assert video.VideoFile(TMP1).audio_codec == "aac"
            os.remove(TMP1)
        except SystemExit as e:
            assert int(str(e)) == 0
            assert abs(video.VideoFile(VIDEO).duration - video.VideoFile(TMP1).duration) < 0.06
            assert video.VideoFile(TMP1).audio_codec == "aac"
            os.remove(TMP1)


def test_main_help():
    with patch.object(sys, "argv", [CMD, "-h"]):
        try:
            reverse.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_bad_option():
    with patch.object(sys, "argv", [CMD, "-i", VIDEO, "--badoption", "yes"]):
        try:
            reverse.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2


def test_main_no_file():
    with patch.object(sys, "argv", [CMD, "-o", TMP1]):
        try:
            reverse.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2
