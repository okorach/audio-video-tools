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

"""Tests of the --format option of the tools that generate a video"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

import mediatools.exceptions as ex
import mediatools.utilities as util
import mediatools.videofile as video
from mediatools import tools


@pytest.fixture
def clip(short_video: str, tmp_path: Path) -> str:
    """A copy of the short video in a temporary folder, where the videos are generated"""
    return str(shutil.copy(short_video, tmp_path / "clip.mp4"))


@pytest.mark.parametrize(("fmt", "expected"), [("mkv", "mkv"), (".AVI", "avi"), (" Mp4 ", "mp4")])
def test_normalize_format(fmt: str, expected: str) -> None:
    """The format is an extension in lowercase without dot"""
    assert util.normalize_format(fmt) == expected


@pytest.mark.parametrize("fmt", ["", "m/p4", "mp4 avi", "toolongformat"])
def test_invalid_format(fmt: str) -> None:
    """Invalid formats are rejected"""
    with pytest.raises(ex.InputError):
        util.normalize_format(fmt)


@pytest.mark.parametrize(
    ("outfile", "fmt", "expected"),
    [(None, None, "mp4"), (None, "mkv", "mkv"), ("out.avi", None, "avi"), ("out.avi", "mkv", "avi"), ("out.AVI", "avi", "avi")],
)
def test_get_output_format(outfile: str | None, fmt: str | None, expected: str) -> None:
    """The format is the one of the output file, else the requested one, else the one of the original file"""
    assert util.get_output_format("dir/clip.mp4", outfile, fmt) == expected


@pytest.mark.parametrize(
    ("outfile", "fmt", "expected"),
    [
        (None, None, os.path.abspath("dir/clip.r90.mp4")),
        (None, "mp4", os.path.abspath("dir/clip.r90.mp4")),
        (None, "mkv", os.path.abspath("dir/clip.mkv")),
        ("dir/out.avi", "mkv", "dir/out.avi"),
    ],
)
def test_format_output_file_name(outfile: str | None, fmt: str | None, expected: str) -> None:
    """The default name has a postfix and the format of the original, or no postfix when the format is changed"""
    assert util.format_output_file_name(outfile, "dir/clip.mp4", "r90", fmt) == expected


def test_encoding_extension() -> None:
    """The extension of an encoding is the format, else the one of the profile, else the one of the original"""
    assert util.get_encoding_extension("clip.avi") == "avi"
    assert util.get_encoding_extension("clip.avi", fmt="mkv") == "mkv"
    assert util.get_encoding_extension("clip.avi", profile="720p") == util.get_profile_extension("720p")


@pytest.mark.parametrize(
    "generate",
    [
        lambda clip, **kw: video.rotate(clip, hw_accel="off", **kw),
        lambda clip, **kw: video.flip(clip, hw_accel="off", **kw),
        lambda clip, **kw: video.speed(clip, 2, hw_accel="off", **kw),
        lambda clip, **kw: video.reverse(clip, hw_accel="off", **kw),
        lambda clip, **kw: video.color_enhance(clip, hw_accel="off", **kw),
        lambda clip, **kw: video.deshake(clip, hw_accel="off", **kw),
    ],
    ids=["rotate", "flip", "speed", "reverse", "enhance", "deshake"],
)
def test_the_format_is_the_extension_of_the_generated_file(clip: str, tmp_path: Path, generate: Callable) -> None:
    """The generated file has the requested format, the original format by default, and the format is not forced to ffmpeg"""
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        assert generate(clip, format="mkv") == str(tmp_path / "clip.mkv")
        assert '"' + str(tmp_path / "clip.mkv") + '"' in run_ffmpeg.call_args.args[0]
        assert " -f " not in run_ffmpeg.call_args.args[0]
        assert generate(clip).endswith(".mp4")
        assert generate(clip, output=str(tmp_path / "out.avi"), format="mkv") == str(tmp_path / "out.avi")


def test_the_format_changes_the_generated_video(clip: str, tmp_path: Path) -> None:
    """A rotated video in another format is really in this format, and the original is not renamed"""
    with patch.object(sys, "argv", ["videotool", "rotate", "-i", clip, "--format", "mkv", "--keepName", "--hw_accel", "off"]):
        tools.videotool()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["clip.mkv", "clip.mp4"]
    assert video.VideoFile(str(tmp_path / "clip.mkv")).resolution.width == video.VideoFile(clip).resolution.height


def test_keep_name_keeps_working_with_the_same_format(clip: str, tmp_path: Path) -> None:
    """Without format change, keepName still renames the original"""
    with patch.object(sys, "argv", ["videotool", "rotate", "-i", clip, "--keepName", "--hw_accel", "off"]):
        tools.videotool()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["clip.before_r90.mp4", "clip.mp4"]


def test_encode_with_a_format(clip: str, tmp_path: Path) -> None:
    """The encode tools generate the requested format, the original one by default"""
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.VideoFile(clip).encode(format="avi", profile=None, hw_accel="off")
    assert run_ffmpeg.call_args.args[0].endswith(f'"{tmp_path / "clip.avi"}"')
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.VideoFile(clip).encode(hw_accel="off")
    assert run_ffmpeg.call_args.args[0].endswith(f'"{tmp_path / "clip.encoded.mp4"}"')
