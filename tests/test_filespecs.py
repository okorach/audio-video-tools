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

import mediatools.audiofile as audio
import mediatools.filespecs as spec
import mediatools.videofile as video

FILE = "it/seal.mp3"


def test_1() -> None:
    """1"""
    allp = list(set(spec.VIDEO_PROPS + spec.AUDIO_PROPS + spec.IMAGE_PROPS))
    specs = audio.AudioFile(FILE).get_properties()
    csv = spec.__to_csv__(specs, allp).split(",")
    assert "192000" in csv
    assert "Seal" in csv
    assert "Crazy" in csv
    # The file name is the absolute path
    assert os.path.abspath(FILE) in csv


def test_2() -> None:
    """2"""
    allp = list(set(spec.VIDEO_PROPS + spec.AUDIO_PROPS + spec.IMAGE_PROPS))
    specs = audio.AudioFile(FILE).get_properties()
    std = spec.__to_std__(specs, allp)
    assert "abitrate            : 187.5 kbits/s" in std
    assert "duration            : 00:05:57.094" in std


def test_specs_on_video_without_audio_does_not_crash(video_no_audio: str) -> None:
    """media-specs does not crash on a video with no audio stream at all (#209)"""
    allp = list(set(spec.VIDEO_PROPS + spec.AUDIO_PROPS + spec.IMAGE_PROPS))
    v = video.VideoFile(video_no_audio)
    specs = v.get_properties()
    assert specs["nb_audio_streams"] == 0
    assert specs["acodec"] is None
    assert v.get_audio_codec() is None
    assert v.get_audio_bitrate() is None
    # Neither of the output formats crashes
    spec.__to_csv__(specs, allp)
    assert "nb_audio_streams    : 0" in spec.__to_std__(specs, allp)
    with patch.object(sys, "argv", ["media-specs", "-i", video_no_audio]):
        spec.main()


def test_specs_supports_multiple_audio_streams(video_two_audio_tracks: str) -> None:
    """media-specs reports every audio stream of a video, not just the first one (#210)"""
    allp = list(set(spec.VIDEO_PROPS + spec.AUDIO_PROPS + spec.IMAGE_PROPS))
    v = video.VideoFile(video_two_audio_tracks)
    specs = v.get_properties()
    assert specs["nb_audio_streams"] == 2
    assert specs["acodec"] == "aac, aac"
    assert len(specs["abitrate"].split(", ")) == 2
    # get_audio_codec()/get_audio_bitrate() (used eg to decide how to re-encode) keep reporting the first stream only
    assert v.get_audio_codec() == "aac"
    assert isinstance(v.get_audio_bitrate(), int)
    # Neither of the output formats crashes on the comma separated, multi-stream abitrate
    spec.__to_csv__(specs, allp)
    assert "nb_audio_streams    : 2" in spec.__to_std__(specs, allp)
    with patch.object(sys, "argv", ["media-specs", "-i", video_two_audio_tracks]):
        spec.main()
