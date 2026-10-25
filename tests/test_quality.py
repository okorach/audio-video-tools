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

"""Tests of the --quality option (constant quality, -crf or -cq, instead of the video bitrate)"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import argparse
import re
from unittest.mock import patch
import pytest
import mediatools.exceptions as ex
import mediatools.mediafile as media
import mediatools.utilities as util
import mediatools.videofile as video
from collections.abc import Callable
from pathlib import Path


@pytest.mark.parametrize(
    "vcodec,quality,expected",
    [
        ("libx264", "high", {"crf": 18}),
        ("libx264", "medium", {"crf": 23}),
        ("libx264", "low", {"crf": 28}),
        ("libx265", "high", {"crf": 23}),
        ("libx265", "medium", {"crf": 28}),
        ("libx265", "low", {"crf": 33}),
        ("h264_nvenc", "medium", {"cq": 23}),
        ("hevc_nvenc", "low", {"cq": 33}),
        ("libx264", "HIGH", {"crf": 18}),
    ],
)
def test_quality_settings(vcodec: str, quality: str, expected: dict) -> None:
    """Quality settings"""
    assert media.get_quality_settings(vcodec, False, quality=quality) == expected


def test_quality_is_high_by_default() -> None:
    """Quality is high by default"""
    assert media.get_quality_settings("libx264") == {"crf": 18}
    assert media.get_quality_settings("libx265") == {"crf": 23}


def test_quality_is_not_used_by_default_with_a_bitrate() -> None:
    """Quality is not used by default with a bitrate"""
    assert media.get_quality_settings("libx264", True) == {}
    # An explicit quality takes precedence over a bitrate
    assert media.get_quality_settings("libx264", True, quality="low") == {"crf": 28}


def test_quality_is_not_applied_to_copied_or_unsupported_codecs() -> None:
    """Quality is not applied to copied or unsupported codecs"""
    assert media.get_quality_settings("copy", quality="low") == {}
    assert media.get_quality_settings("libxvid", quality="low") == {}
    assert media.get_quality_settings("libxvid") == {}


def test_invalid_quality() -> None:
    """Invalid quality"""
    with pytest.raises(ex.InputError):
        media.get_quality_settings("libx264", quality="ultra")


def test_quality_triggers_the_encoding() -> None:
    """Quality triggers the encoding"""
    assert media._must_encode_video(quality="low")  # pylint: disable=protected-access
    assert not media._must_encode_video(quality="low", vcodec="copy")  # pylint: disable=protected-access
    assert not media._must_encode_video()  # pylint: disable=protected-access


def test_quality_option() -> None:
    """Quality option"""
    parser = argparse.ArgumentParser()
    video.add_video_args(parser)
    assert vars(parser.parse_args([]))["quality"] is None
    assert vars(parser.parse_args(["--quality", "Medium"]))["quality"] == "medium"
    with pytest.raises(SystemExit):
        parser.parse_args(["--quality", "ultra"])


@pytest.fixture
def ffmpeg_cmd() -> Callable[..., str]:
    """Runs VideoFile.encode() without running ffmpeg, and returns the ffmpeg parameters"""

    def run(short_video: str, tmp_path: Path, **kwargs: object) -> str:
        """Encodes a video without running ffmpeg and returns the ffmpeg parameters"""
        with patch.object(util, "run_ffmpeg") as run_ffmpeg:
            video.VideoFile(short_video).encode(target_file=str(tmp_path / "out.mp4"), hw_accel="off", **kwargs)
        return run_ffmpeg.call_args.args[0]

    return run


def crf(cmd: str) -> str | None:
    """Returns the constant quality (-crf) of an ffmpeg command, None if there is none"""
    m = re.search(r'-crf "?(\d+)', cmd)
    return m.group(1) if m else None


def test_encode_default_quality_is_high(short_video: str, tmp_path: Path, ffmpeg_cmd: Callable[..., str]) -> None:
    """Encode default quality is high"""
    cmd = ffmpeg_cmd(short_video, tmp_path, vcodec="x264", width=160)
    assert crf(cmd) == "18"
    assert "-b:v" not in cmd


def test_encode_x265_qualities(short_video: str, tmp_path: Path, ffmpeg_cmd: Callable[..., str]) -> None:
    """Encode x265 qualities"""
    for quality, expected in (("high", "23"), ("medium", "28"), ("low", "33")):
        assert crf(ffmpeg_cmd(short_video, tmp_path, vcodec="x265", quality=quality)) == expected


def test_encode_quality_alone_encodes_the_video(short_video: str, tmp_path: Path, ffmpeg_cmd: Callable[..., str]) -> None:
    """Encode quality alone encodes the video"""
    cmd = ffmpeg_cmd(short_video, tmp_path, quality="low")
    assert crf(cmd) == "28"  # h264 by default
    assert "libx264" in cmd


def test_encode_bitrate_without_quality_keeps_the_bitrate(short_video: str, tmp_path: Path, ffmpeg_cmd: Callable[..., str]) -> None:
    """Encode bitrate without quality keeps the bitrate"""
    cmd = ffmpeg_cmd(short_video, tmp_path, vcodec="x264", vbitrate="2000k")
    assert crf(cmd) is None
    assert '-b:v "2000k"' in cmd


def test_encode_quality_replaces_the_bitrate(short_video: str, tmp_path: Path, ffmpeg_cmd: Callable[..., str]) -> None:
    """Encode quality replaces the bitrate"""
    cmd = ffmpeg_cmd(short_video, tmp_path, vcodec="x264", vbitrate="2000k", quality="medium")
    assert crf(cmd) == "23"
    assert "-b:v" not in cmd


def test_encode_with_a_profile_bitrate(short_video: str, tmp_path: Path) -> None:
    """Encode with a profile bitrate"""
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.VideoFile(short_video).encode(target_file=str(tmp_path / "out.mp4"), profile="720p", vcodec="x264", hw_accel="off")
    assert crf(run_ffmpeg.call_args.args[0]) is None
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.VideoFile(short_video).encode(target_file=str(tmp_path / "out.mp4"), profile="720p", vcodec="x264", quality="low", hw_accel="off")
    cmd = run_ffmpeg.call_args.args[0]
    assert crf(cmd) == "28"
    assert "-b:v" not in cmd


def test_encode_hardware_accelerated_uses_cq(short_video: str, tmp_path: Path) -> None:
    """Encode hardware accelerated uses cq"""
    with patch.object(util, "run_ffmpeg") as run_ffmpeg, patch.object(util, "use_hardware_accel", return_value=True):
        video.VideoFile(short_video).encode(target_file=str(tmp_path / "out.mp4"), vcodec="x265", quality="medium")
    cmd = run_ffmpeg.call_args.args[0]
    assert "hevc_nvenc" in cmd
    assert '-cq "28"' in cmd


def test_copy_does_not_use_the_quality(short_video: str, tmp_path: Path, ffmpeg_cmd: Callable[..., str]) -> None:
    """Copy does not use the quality"""
    cmd = ffmpeg_cmd(short_video, tmp_path, vcodec="copy", acodec="copy")
    assert crf(cmd) is None


def test_encode_real_video_low_quality_is_smaller(short_video: str, tmp_path: Path) -> None:
    """Encode real video low quality is smaller"""
    sizes = {}
    for quality in ("high", "low"):
        out = video.VideoFile(short_video).encode(target_file=str(tmp_path / f"{quality}.mp4"), vcodec="x264", quality=quality, hw_accel="off")
        sizes[quality] = video.VideoFile(out).size()
    assert 0 < sizes["low"] < sizes["high"]
