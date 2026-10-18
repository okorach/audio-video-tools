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
from unittest.mock import MagicMock, patch
import pytest
from mediatools import speed
import mediatools.utilities as util
import mediatools.videofile as video

CMD = "video-speed"
VIDEO = "it" + os.sep + "video-360p-1.mp4"
TMP1 = util.get_tmp_file() + ".mp4"


def assert_duration(speed_factor):
    """The duration of the output is the duration of the source divided by the speed factor, to the precision of 2 frames
    (the audio, when kept, can be slightly longer than the video)"""
    expected = video.VideoFile(VIDEO).duration / speed_factor
    assert abs(expected - video.VideoFile(TMP1).duration) < 0.1


def test_main():
    with patch.object(sys, "argv", [CMD, "-p", "360p", "-i", VIDEO, "--speed", "2"]):
        speed.main()
        assert True


def test_main_with_output():
    with patch.object(sys, "argv", [CMD, "-p", "360p", "-i", VIDEO, "-o", TMP1, "--speed", "200%"]):
        speed.main()
        assert_duration(2)
        assert video.VideoFile(TMP1).audio_codec is None
        os.remove(TMP1)


def test_slowmo():
    with patch.object(sys, "argv", [CMD, "-p", "360p", "-i", VIDEO, "-o", TMP1, "--speed", "50%"]):
        speed.main()
        assert_duration(0.5)
        assert video.VideoFile(TMP1).audio_codec is None
        os.remove(TMP1)


def test_keep_audio():
    with patch.object(sys, "argv", [CMD, "-p", "360p", "-i", VIDEO, "-o", TMP1, "-k", "--speed", "4"]):
        speed.main()
        # TODO - Truncate audio when video is shorter, and adjust tests
        assert_duration(4)
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


def test_speed_api_removes_audio():
    output = video.speed(VIDEO, "2", output=TMP1)
    assert video.VideoFile(output).audio_codec is None
    os.remove(output)


def test_speed_api_keep_audio():
    output = video.speed(VIDEO, "2", output=TMP1, mute=False)
    assert video.VideoFile(output).audio_codec is not None
    os.remove(output)


def test_speed_api_keeps_source_size_and_bitrate(monkeypatch):
    encode = MagicMock(return_value="out.mp4")
    monkeypatch.setattr(video.VideoFile, "encode", encode)
    monkeypatch.setattr(video.VideoFile, "__init__", lambda self, _filename, **_k: setattr(self, "video_bitrate", 1234567))
    video.speed(VIDEO, "2", output=TMP1)
    assert encode.call_args.kwargs["vbitrate"] == 1234567
    assert "width" not in encode.call_args.kwargs
    video.speed(VIDEO, "2", output=TMP1, vbitrate=999)
    assert encode.call_args.kwargs["vbitrate"] == 999
    video.speed(VIDEO, "2", output=TMP1, profile="360p")
    assert "vbitrate" not in encode.call_args.kwargs


def test_speed_real_video_same_size_and_bitrate(short_video, tmp_path):
    source = video.VideoFile(short_video)
    output = video.VideoFile(video.speed(short_video, "2", output=str(tmp_path / "fast.mp4")))
    assert output.get_width() == source.get_width()
    assert output.video_bitrate == pytest.approx(source.video_bitrate, rel=0.5)


def test_speed_default_output_name(monkeypatch):
    encode = MagicMock(return_value="out.mp4")
    monkeypatch.setattr(video.VideoFile, "encode", encode)
    monkeypatch.setattr(video.VideoFile, "__init__", lambda self, _filename, **_k: setattr(self, "video_bitrate", None))
    video.speed("dir" + os.sep + "foo.mp4", "2.5")
    assert os.path.basename(encode.call_args.kwargs["target_file"]) == "foo.2.5.mp4"
