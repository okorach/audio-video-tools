#!python3
#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
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
import subprocess
from unittest.mock import patch
from mediatools import tools
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.audiofile as audio
from mediatools import log

TMP_VID = util.get_tmp_file() + ".mp4"
TMP_AUDIO = util.get_tmp_file() + ".mp3"


def get_video():
    return "it" + os.sep + "video-1920x1080.mp4"


def test_encode_size():
    vid_o = video.VideoFile(get_video())
    util.HW_ACCEL = None
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution="1280x720", start=1, stop=2))
    assert vid2_o.resolution.width == 1280
    assert abs(vid2_o.duration - 1) < 0.1
    os.remove(TMP_VID)


def test_encode_bitrate():
    vid_o = video.VideoFile(get_video())
    util.HW_ACCEL = None
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution="640x360", vbitrate="1000k", abitrate="64k", start=1, stop=4))
    assert abs(vid2_o.video_bitrate - 1024 * 1024) < 200000
    assert abs(vid2_o.audio_bitrate - 64 * 1024) < 30000
    os.remove(TMP_VID)


def test_encode_acodec():
    vid_o = video.VideoFile(get_video())
    util.HW_ACCEL = None
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution="640x360", acodec="mp3", deinterlace=True, start=1, stop=2))
    assert vid2_o.audio_codec == "mp3"
    os.remove(TMP_VID)


def test_encode_vcodec():
    vid_o = video.VideoFile(get_video())
    util.HW_ACCEL = None
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution="640x360", vcodec="h265", deinterlace=True, start=1, stop=2))
    assert vid2_o.video_codec == "hevc"
    os.remove(TMP_VID)


def test_hw_accel_2(monkeypatch):
    """The hardware acceleration is available according to the check: the encoding succeeds in any case, on the GPU or,
    if the GPU command fails (no GPU), on the CPU"""
    monkeypatch.setattr(util, "HW_ACCEL", True)
    vid_o = video.VideoFile(get_video())
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution="640x360", abitrate="64k", start=1, stop=2))
    assert abs(vid2_o.duration - 1) < 0.1
    os.remove(TMP_VID)


def test_main_file(short_video):
    file1 = short_video
    try:
        with patch.object(
            sys, "argv", ["videotool", "profile-encode", "-g", "4", "-p", "1mbps", "-i", file1, "--hw_accel", "off", "--resolution", "640x360"]
        ):
            tools.videotool()
        assert True
    except subprocess.CalledProcessError:
        # Encoding will fail... just to cover some source code
        assert False


def test_main_file_audio():

    file1 = "it" + os.sep + "seal.mp3"
    with patch.object(sys, "argv", ["videotool", "profile-encode", "-p", "mp3_128k", "-i", file1, "--outputfile", TMP_AUDIO, "--hw_accel", "off"]):
        tools.videotool()
    # log.set_logger("tests")
    # log.logger.setLevel(log.get_logging_level(4))
    audio_f = audio.AudioFile(TMP_AUDIO)
    audio_f.get_specs()
    assert audio_f.acodec == "mp3"
    assert audio_f.format == "mp3"
    os.remove(TMP_AUDIO)


def test_main_dir_timeranges_1(video_5s):
    file1 = video_5s
    try:
        with patch.object(
            sys,
            "argv",
            [
                "videotool",
                "profile-encode",
                "-p",
                "1mbps",
                "-i",
                file1,
                "--hw_accel",
                "off",
                "--resolution",
                "640x360",
                "--timeranges",
                "00:02-00:04",
                "-g",
                "4",
            ],
        ):
            tools.videotool()
        # Can't delete output file, don't know the name
        assert True
    except subprocess.CalledProcessError:
        assert False


def test_main_dir_timeranges_2(video_5s):
    log.set_logger("tests")
    log.logger.setLevel(log.get_logging_level(4))
    file1 = video_5s
    output = f"{file1}.out.mp4"
    try:
        with patch.object(
            sys,
            "argv",
            [
                "videotool",
                "profile-encode",
                "-p",
                "1mbps",
                "-i",
                file1,
                "--resolution",
                "640x360",
                "--hw_accel",
                "off",
                "--timeranges",
                "00:00-00:01,00:02-00:04",
            ],
            "-o",
            output,
        ):
            tools.videotool()
        # Output file is hardcoded for now :-(
        os.remove(file1.replace("video-5s.mp4", "video-5s.combined.mp4"))
        assert True
    except subprocess.CalledProcessError:
        assert False
