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
import pytest
from unittest.mock import patch
from mediatools import tools
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.audiofile as audio

VIDEO = "it" + os.sep + "video-720p.mp4"
AUDIO = "it" + os.sep + "seal.mp3"
TMPV = util.get_tmp_file() + ".mp4"
TMPA = util.get_tmp_file() + ".mp3"


def test_main_v():
    with patch.object(sys, "argv", ["videotool", "cut", "--start", "10", "--stop", "20", "-i", VIDEO]):
        tools.videotool()
        assert True


def test_main_a():
    with patch.object(sys, "argv", ["videotool", "cut", "--start", "10", "--stop", "20", "-i", AUDIO]):
        tools.videotool()
        assert True


def test_main_v_with_output():
    start, stop = 3, 7
    with patch.object(sys, "argv", ["videotool", "cut", "--start", str(start), "--stop", str(stop), "-i", VIDEO, "-o", TMPV]):
        tools.videotool()
        v = video.VideoFile(TMPV)
        v.get_specs()
        assert abs(v.duration + start - stop) < 0.06
        os.remove(TMPV)


def test_main_a_with_output():
    start, stop = 30, 60
    with patch.object(sys, "argv", ["videotool", "cut", "--start", str(start), "--stop", str(stop), "-i", AUDIO, "-o", TMPA]):
        tools.videotool()
        audiofile = audio.AudioFile(TMPA)
        audiofile.get_specs()
        assert abs(audiofile.duration + start - stop) < 0.06
        os.remove(TMPA)


def test_main_help():
    with patch.object(sys, "argv", ["videotool", "cut", "-h"]):
        try:
            tools.videotool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_bad_option():
    with patch.object(sys, "argv", ["videotool", "cut", "-i", VIDEO, "--badoption", "yes"]):
        try:
            tools.videotool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2


def test_main_no_file():
    with patch.object(sys, "argv", ["videotool", "cut", "-o", TMPA]):
        try:
            tools.videotool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2


def test_output_file_is_used_for_a_single_range():
    """-o is the name of the file generated with --start and --stop"""
    with (
        patch.object(sys, "argv", ["videotool", "cut", "--start", "1", "--stop", "2", "-i", VIDEO, "-o", "out.mp4"]),
        patch("mediatools.avfile.cut") as av_cut,
    ):
        tools.videotool()
    assert av_cut.call_count == 1
    assert av_cut.call_args.kwargs["output"] == "out.mp4"
    assert av_cut.call_args.kwargs["start"] == "1"
    assert av_cut.call_args.kwargs["stop"] == "2"


def test_time_ranges():
    """All the time ranges are cut by one call per file"""
    with patch.object(sys, "argv", ["videotool", "cut", "--timeranges", "0-1,2-3", "-i", VIDEO, AUDIO]), patch("mediatools.avfile.cut") as av_cut:
        tools.videotool()
    assert [c.args[0] for c in av_cut.call_args_list] == [VIDEO, AUDIO]
    for call in av_cut.call_args_list:
        assert call.kwargs["timeranges"] == "0-1,2-3"
        assert "start" not in call.kwargs
        assert "stop" not in call.kwargs
        assert call.kwargs["output"] is None


def test_output_file_with_several_ranges():
    """-o can't be used with several time ranges"""
    with patch.object(sys, "argv", ["videotool", "cut", "--timeranges", "0-1,2-3", "-i", VIDEO, "-o", "out.mp4"]), pytest.raises(SystemExit) as e:
        tools.videotool()
    assert e.value.code == 2


def test_missing_range():
    """--start and --stop or --timeranges is mandatory"""
    with patch.object(sys, "argv", ["videotool", "cut", "-i", VIDEO]), pytest.raises(SystemExit) as e:
        tools.videotool()
    assert e.value.code == 1
