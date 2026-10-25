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
from unittest.mock import patch
import pytest
from mediatools import tools
import mediatools.utilities as util
import mediatools.videofile as video

VIDEO = "it" + os.sep + "video-360p-1.mp4"
TMP1 = util.get_tmp_file() + ".mp4"


@pytest.fixture(autouse=True)
def use_short_video(short_video: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """The tests don't depend on a specific video: reversing a short video is much faster"""
    monkeypatch.setattr(sys.modules[__name__], "VIDEO", short_video)


def test_main() -> None:
    """Main"""
    with patch.object(sys, "argv", ["videotool", "reverse", "-g", "2", "-i", VIDEO]):
        try:
            assert tools.videotool() is None
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_with_output() -> None:
    """Main with output"""
    with patch.object(sys, "argv", ["videotool", "reverse", "-g", "2", "-i", VIDEO, "-o", TMP1]):
        try:
            tools.videotool()
            assert abs(video.VideoFile(VIDEO).duration - video.VideoFile(TMP1).duration) < 0.06
            assert video.VideoFile(TMP1).audio_codec is None
            os.remove(TMP1)
        except SystemExit as e:
            assert int(str(e)) == 0
            assert abs(video.VideoFile(VIDEO).duration - video.VideoFile(TMP1).duration) < 0.06
            assert video.VideoFile(TMP1).audio_codec is None
            os.remove(TMP1)


def test_keep_audio() -> None:
    """Keep audio"""
    with patch.object(sys, "argv", ["videotool", "reverse", "-g", "2", "-i", VIDEO, "-o", TMP1, "-k"]):
        try:
            tools.videotool()
            assert abs(video.VideoFile(VIDEO).duration - video.VideoFile(TMP1).duration) < 0.06
            assert video.VideoFile(TMP1).audio_codec == "aac"
            os.remove(TMP1)
        except SystemExit as e:
            assert int(str(e)) == 0
            assert abs(video.VideoFile(VIDEO).duration - video.VideoFile(TMP1).duration) < 0.06
            assert video.VideoFile(TMP1).audio_codec == "aac"
            os.remove(TMP1)


def test_main_help() -> None:
    """Main help"""
    with patch.object(sys, "argv", ["videotool", "reverse", "-h"]):
        with pytest.raises(SystemExit) as e:
            tools.videotool()
        assert int(str(e.value)) == 0


def test_main_bad_option() -> None:
    """Main bad option"""
    with patch.object(sys, "argv", ["videotool", "reverse", "-i", VIDEO, "--badoption", "yes"]):
        with pytest.raises(SystemExit) as e:
            tools.videotool()
        assert int(str(e.value)) == 2


def test_main_no_file() -> None:
    """Main no file"""
    with patch.object(sys, "argv", ["videotool", "reverse", "-o", TMP1]):
        with pytest.raises(SystemExit) as e:
            tools.videotool()
        assert int(str(e.value)) == 2


def test_reverse_api_removes_audio() -> None:
    """Reverse api removes audio"""
    output = video.reverse(VIDEO, output=TMP1)
    assert video.VideoFile(output).audio_codec is None
    os.remove(output)


def test_reverse_api_keep_audio() -> None:
    """Reverse api keep audio"""
    output = video.reverse(VIDEO, output=TMP1, mute=False)
    assert video.VideoFile(output).audio_codec is not None
    os.remove(output)
