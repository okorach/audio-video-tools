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

"""Tests of the video flip (videotool flip)"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import re
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
import mediatools.exceptions as ex
import mediatools.utilities as util
import mediatools.videofile as video
from mediatools import tools


@pytest.fixture
def clip(short_video, tmp_path) -> str:
    """A copy of the 320x180 short video in a temporary folder, where the flipped videos are generated"""
    return shutil.copy(short_video, tmp_path / "clip.mp4").__str__()


def size(file: str) -> tuple[int, int]:
    v = video.VideoFile(file)
    return (v.resolution.width, v.resolution.height)


def run(*args: str) -> None:
    with patch.object(sys, "argv", ["videotool", "flip", *args]):
        tools.videotool()


def first_frame(file: str) -> np.ndarray:
    """The first frame of a video, as a (height, width, 3) array"""
    width, height = size(file)
    raw = subprocess.run(
        [util.get_ffmpeg(), "-v", "error", "-i", file, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True
    ).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 3).astype(int)


def difference(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.abs(a - b).mean())


# ------------------------------------------------ Directions


@pytest.mark.parametrize(
    "direction,expected", [("leftright", "leftright"), ("topbottom", "topbottom"), ("LeftRight", "leftright"), (None, "leftright")]
)
def test_normalize_direction(direction, expected):
    assert video.normalize_flip_direction(direction) == expected


@pytest.mark.parametrize("direction", ["", "left", "rightleft", "updown", "diagonal"])
def test_invalid_direction(direction):
    with pytest.raises(ex.InputError, match="Invalid flip direction"):
        video.normalize_flip_direction(direction)


@pytest.mark.parametrize("direction,expected", [("leftright", "hflip"), ("topbottom", "vflip"), (None, "hflip")])
def test_flip_filter(direction, expected):
    assert video.get_flip_filter(direction) == expected


# ------------------------------------------------ The flipped video


def test_flip_default_is_left_to_right(clip):
    out = video.flip(clip)
    assert out == clip.replace("clip.mp4", "clip.flip_leftright.mp4")
    assert size(out) == (320, 180)  # The size is unchanged
    source, flipped = first_frame(clip), first_frame(out)
    assert difference(flipped, source[:, ::-1]) < difference(flipped, source)
    assert difference(flipped, source[:, ::-1]) < 20


def test_flip_top_to_bottom(clip):
    out = video.flip(clip, direction="topbottom")
    assert out == clip.replace("clip.mp4", "clip.flip_topbottom.mp4")
    source, flipped = first_frame(clip), first_frame(out)
    assert difference(flipped, source[::-1]) < difference(flipped, source)
    assert difference(flipped, source[::-1]) < 20
    assert difference(flipped, source[:, ::-1]) > difference(flipped, source[::-1])


def test_flip_twice_gives_the_original(clip, tmp_path):
    once = video.flip(clip, str(tmp_path / "once.mp4"), hw_accel="off")
    twice = video.flip(once, str(tmp_path / "twice.mp4"), hw_accel="off")
    assert difference(first_frame(twice), first_frame(clip)) < 20


def test_flip_keeps_audio_fps_codec_and_extension(clip):
    out = video.flip(clip, hw_accel="off")
    original, flipped = video.VideoFile(clip), video.VideoFile(out)
    assert flipped.get_fps() == original.get_fps()
    assert flipped.get_video_codec() == original.get_video_codec()
    assert any(s["codec_type"] == "audio" for s in flipped.specs["streams"])
    assert Path(out).suffix == ".mp4"


def test_flip_fps_resolution_and_codec(clip):
    out = video.flip(clip, fps="10", resolution="160x90", vcodec="h265", hw_accel="off")
    assert float(video.VideoFile(out).get_fps()) == 10
    assert size(out) == (160, 90)
    assert video.VideoFile(out).get_video_codec() == "hevc"


def test_flip_output_file(clip, tmp_path):
    target = str(tmp_path / "flipped.mp4")
    assert video.flip(clip, target) == target
    assert Path(target).exists()


def test_flip_keep_name(clip):
    out = video.flip(clip, direction="topbottom", keep_name=True)
    assert out == clip
    source = first_frame(clip.replace("clip.mp4", "clip.before_flip_topbottom.mp4"))
    assert difference(first_frame(clip), source[::-1]) < difference(first_frame(clip), source)
    assert not Path(clip.replace("clip.mp4", "clip.flip_topbottom.mp4")).exists()


def test_flip_keep_name_with_output_is_rejected(clip, tmp_path):
    with pytest.raises(ex.InputError):
        video.flip(clip, str(tmp_path / "out.mp4"), keep_name=True)


# ------------------------------------------------ Quality and hardware acceleration


def test_flip_quality_is_high_by_default(clip):
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.flip(clip, hw_accel="off")
    cmd = run_ffmpeg.call_args.args[0]
    assert re.search(r'-crf "?18', cmd)
    assert '-vf "hflip"' in cmd or "hflip" in cmd
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.flip(clip, direction="topbottom", quality="low", hw_accel="off")
    cmd = run_ffmpeg.call_args.args[0]
    assert re.search(r'-crf "?28', cmd)
    assert "vflip" in cmd


def test_flip_is_encoded_by_the_gpu_and_filtered_by_the_cpu(clip):
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.flip(clip, hw_accel="on", resolution="90x160")
    cmd = run_ffmpeg.call_args.args[0]
    assert "h264_nvenc" in cmd
    assert re.search(r'-cq "?18', cmd)
    assert "hflip" in cmd
    # The frames are decoded on the CPU: no GPU decoding nor GPU filter
    assert "-hwaccel" not in cmd
    assert "scale_cuda" not in cmd
    assert '-s "90x160"' in cmd


def test_flip_runs_again_on_the_cpu_when_the_gpu_fails(clip, tmp_path):
    attempts = []

    def run_os_cmd(cmd, duration=None):
        attempts.append(cmd)
        if "nvenc" in cmd:
            raise subprocess.CalledProcessError(1, cmd)

    with patch("mediatools.utilities.run_os_cmd", side_effect=run_os_cmd), patch.object(util, "check_hardware_accel", return_value=True):
        out = video.flip(clip, output=str(tmp_path / "out.mp4"))
    assert out == str(tmp_path / "out.mp4")
    assert "nvenc" in attempts[0]
    assert "nvenc" not in attempts[-1]
    assert "hflip" in attempts[-1]


# ------------------------------------------------ The command


def test_flip_is_a_videotool_action():
    assert "flip" in tools.VIDEO_ACTIONS


def test_command_default(clip):
    run("-i", clip, "--hw_accel", "off")
    assert Path(clip.replace("clip.mp4", "clip.flip_leftright.mp4")).exists()


@pytest.mark.parametrize("direction", ["leftright", "topbottom", "TopBottom"])
def test_command_directions(clip, direction):
    run("-i", clip, "--direction", direction, "--hw_accel", "off")
    assert Path(clip.replace("clip.mp4", f"clip.flip_{direction.lower()}.mp4")).exists()


@pytest.mark.parametrize("direction", ["left", "updown", "90"])
def test_command_rejects_invalid_directions(clip, direction):
    with pytest.raises(SystemExit) as e:
        run("-i", clip, "--direction", direction)
    assert e.value.code == 2


def test_command_keep_name(clip):
    run("-i", clip, "--keepName", "--hw_accel", "off")
    assert Path(clip.replace("clip.mp4", "clip.before_flip_leftright.mp4")).exists()
    assert Path(clip).exists()


def test_command_standard_options(clip):
    run("-i", clip, "--fps", "12", "--resolution", "90x160", "--quality", "low", "--vcodec", "x265", "--hw_accel", "off")
    out = video.VideoFile(clip.replace("clip.mp4", "clip.flip_leftright.mp4"))
    assert size(out.filename) == (90, 160)
    assert float(out.get_fps()) == 12
    assert out.get_video_codec() == "hevc"


@pytest.mark.parametrize("mode", ["auto", "on", "off"])
def test_command_hw_accel_option(clip, mode):
    with patch.object(video, "flip", return_value=clip) as flip:
        run("-i", clip, "--hw_accel", mode)
    assert flip.call_args.kwargs["hw_accel"] == mode


def test_command_invalid_options(clip):
    for args in (["--hw_accel", "maybe"], ["--quality", "ultra"]):
        with pytest.raises(SystemExit) as e:
            run("-i", clip, *args)
        assert e.value.code == 2


def test_command_several_files_and_directories(short_video, tmp_path):
    folder = tmp_path / "videos"
    (folder / "sub").mkdir(parents=True)
    first = shutil.copy(short_video, folder / "a.mp4")
    second = shutil.copy(short_video, folder / "sub" / "b.mp4")
    third = shutil.copy(short_video, tmp_path / "c.mp4")
    run("-i", str(folder), str(third), "--direction", "topbottom", "--hw_accel", "off")
    for f in (first, second, third):
        assert Path(str(f).replace(".mp4", ".flip_topbottom.mp4")).exists()


def test_command_output_file_with_several_files_is_rejected(short_video, tmp_path):
    first = shutil.copy(short_video, tmp_path / "a.mp4")
    second = shutil.copy(short_video, tmp_path / "b.mp4")
    with pytest.raises(SystemExit) as e:
        run("-i", str(first), str(second), "-o", str(tmp_path / "out.mp4"))
    assert e.value.code == 2


def test_flipped_files_keep_the_dates_of_the_original(clip):
    import os  # pylint: disable=import-outside-toplevel
    from datetime import datetime  # pylint: disable=import-outside-toplevel

    old = datetime(2020, 5, 17, 10, 30, 0).timestamp()
    os.utime(clip, (old, old))
    out = video.flip(clip, hw_accel="off")
    assert abs(os.stat(out).st_mtime - old) < 2
