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

"""Tests of the video rotation (videotool rotate)"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import re
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
import mediatools.exceptions as ex
import mediatools.media_config as conf
import mediatools.utilities as util
import mediatools.videofile as video
from mediatools import tools


@pytest.fixture
def clip(short_video: str, tmp_path: Path) -> str:
    """A copy of the 320x180 short video in a temporary folder, where the rotated videos are generated"""
    return str(shutil.copy(short_video, tmp_path / "clip.mp4"))


def size(file: str) -> tuple[int, int]:
    """Returns the width and the height of a video"""
    v = video.VideoFile(file)
    return (v.resolution.width, v.resolution.height)


def run(*args: str) -> None:
    """Runs the command with the arguments given"""
    with patch.object(sys, "argv", ["videotool", "rotate", *args]):
        tools.videotool()


@pytest.mark.parametrize("angle,expected", [(90, 90), ("90", 90), (180, 180), (270, 270), (-90, 270), ("-90", 270), (None, 90)])
def test_normalize_angle(angle: int | str | None, expected: int) -> None:
    """Normalize angle"""
    assert video.normalize_rotation_angle(angle) == expected


@pytest.mark.parametrize("angle", [0, 45, 360, -180, 91, "abc", ""])
def test_invalid_angle(angle: int | str) -> None:
    """Invalid angle"""
    with pytest.raises(ex.InputError):
        video.normalize_rotation_angle(angle)


@pytest.mark.parametrize("angle,expected", [(90, "transpose=1"), (-90, "transpose=2"), (270, "transpose=2"), (180, "hflip,vflip")])
def test_rotation_filter(angle: int, expected: str) -> None:
    """Rotation filter"""
    assert video.get_rotation_filter(angle) == expected


def test_rotate_90_default_name(clip: str) -> None:
    """Rotate 90 default name"""
    out = video.rotate(clip)
    assert out == clip.replace("clip.mp4", "clip.r90.mp4")
    assert size(out) == (180, 320)
    assert size(clip) == (320, 180)  # The original is untouched


@pytest.mark.parametrize("angle,postfix,expected", [(180, "r180", (320, 180)), (270, "r270", (180, 320)), (-90, "r270", (180, 320))])
def test_rotate_angles(clip: str, angle: int, postfix: str, expected: tuple) -> None:
    """Rotate angles"""
    out = video.rotate(clip, angle=angle)
    assert out == clip.replace("clip.mp4", f"clip.{postfix}.mp4")
    assert size(out) == expected


def test_rotate_keeps_audio_fps_and_extension(clip: str) -> None:
    """Rotate keeps audio fps and extension"""
    out = video.rotate(clip)
    original, rotated = video.VideoFile(clip), video.VideoFile(out)
    assert rotated.get_fps() == original.get_fps()
    assert any(s["codec_type"] == "audio" for s in rotated.specs["streams"])
    assert Path(out).suffix == ".mp4"


def test_rotate_fps_and_resolution(clip: str) -> None:
    """Rotate fps and resolution"""
    out = video.rotate(clip, fps="10", resolution="90x160")
    assert float(video.VideoFile(out).get_fps()) == 10
    assert size(out) == (90, 160)


def test_rotate_output_file(clip: str, tmp_path: Path) -> None:
    """Rotate output file"""
    target = str(tmp_path / "rotated.mp4")
    assert video.rotate(clip, target, 90) == target
    assert size(target) == (180, 320)


def test_rotate_keep_name(clip: str) -> None:
    """Rotate keep name"""
    out = video.rotate(clip, angle=90, keep_name=True)
    assert out == clip
    assert size(clip) == (180, 320)  # The rotated video has the name of the original
    before = clip.replace("clip.mp4", "clip.before_r90.mp4")
    assert size(before) == (320, 180)
    assert not Path(clip.replace("clip.mp4", "clip.r90.mp4")).exists()


def test_rotate_keep_name_with_output_is_rejected(clip: str, tmp_path: Path) -> None:
    """Rotate keep name with output is rejected"""
    with pytest.raises(ex.InputError):
        video.rotate(clip, str(tmp_path / "out.mp4"), 90, keep_name=True)


def test_rotate_quality_is_high_by_default(clip: str, tmp_path: Path) -> None:
    """Rotate quality is high by default"""
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.rotate(clip, hw_accel="off")
    cmd = run_ffmpeg.call_args.args[0]
    assert re.search(r'-crf "?18', cmd)
    assert "transpose=1" in cmd
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.rotate(clip, quality="low", hw_accel="off")
    assert re.search(r'-crf "?28', run_ffmpeg.call_args.args[0])


def test_rotate_is_encoded_by_the_gpu_and_filtered_by_the_cpu(clip: str) -> None:
    """Rotate is encoded by the gpu and filtered by the cpu"""
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.rotate(clip, hw_accel="on", resolution="90x160")
    cmd = run_ffmpeg.call_args.args[0]
    assert "h264_nvenc" in cmd
    assert re.search(r'-cq "?18', cmd)
    assert "transpose=1" in cmd
    # The frames are decoded on the CPU: no GPU decoding nor GPU filter
    assert "-hwaccel" not in cmd
    assert "scale_cuda" not in cmd
    assert '-s "90x160"' in cmd


def test_rotate_is_not_encoded_by_the_gpu_when_off(clip: str) -> None:
    """Rotate is not encoded by the gpu when off"""
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.rotate(clip, hw_accel="off")
    assert "nvenc" not in run_ffmpeg.call_args.args[0]


def test_rotate_runs_again_on_the_cpu_when_the_gpu_fails(clip: str, tmp_path: Path) -> None:
    """Rotate runs again on the cpu when the gpu fails"""
    attempts = []

    def run_os_cmd(cmd: str, duration: float | None = None) -> None:
        """Replaces the execution of the commands: records them and fails for the ones using the GPU encoder"""
        attempts.append(cmd)
        if "nvenc" in cmd:
            raise subprocess.CalledProcessError(1, cmd)

    with patch("mediatools.utilities.run_os_cmd", side_effect=run_os_cmd), patch.object(util, "check_hardware_accel", return_value=True):
        out = video.rotate(clip, output=str(tmp_path / "out.mp4"))
    assert out == str(tmp_path / "out.mp4")
    assert "nvenc" in attempts[0]
    assert "nvenc" not in attempts[-1]
    assert "transpose=1" in attempts[-1]


def test_rotate_failure_with_the_gpu_forced_is_raised(clip: str, tmp_path: Path) -> None:
    """Rotate failure with the gpu forced is raised"""

    def run_os_cmd(cmd: str, duration: float | None = None) -> None:
        """Replaces the execution of the commands: they all fail"""
        raise subprocess.CalledProcessError(1, cmd)

    with patch("mediatools.utilities.run_os_cmd", side_effect=run_os_cmd), pytest.raises(subprocess.CalledProcessError):
        video.rotate(clip, output=str(tmp_path / "out.mp4"), hw_accel="on")


def test_command_default_angle(clip: str) -> None:
    """Command default angle"""
    run("-i", clip)
    out = clip.replace("clip.mp4", "clip.r90.mp4")
    assert size(out) == (180, 320)


@pytest.mark.parametrize("angle,postfix", [("-90", "r270"), ("270", "r270"), ("180", "r180")])
def test_command_angles(clip: str, angle: str, postfix: str) -> None:
    """Command angles"""
    run("-i", clip, "--angle", angle)
    assert Path(clip.replace("clip.mp4", f"clip.{postfix}.mp4")).exists()


@pytest.mark.parametrize("angle", ["0", "45", "360", "abc"])
def test_command_rejects_invalid_angles(clip: str, angle: str) -> None:
    """Command rejects invalid angles"""
    with pytest.raises(SystemExit) as e:
        run("-i", clip, "--angle", angle)
    assert e.value.code == 2
    assert not Path(clip.replace("clip.mp4", "clip.r90.mp4")).exists()


def test_command_keep_name(clip: str) -> None:
    """Command keep name"""
    run("-i", clip, "--keepName")
    assert size(clip) == (180, 320)
    assert Path(clip.replace("clip.mp4", "clip.before_r90.mp4")).exists()


def test_command_several_files_and_directories(short_video: str, tmp_path: Path) -> None:
    """Command several files and directories"""
    folder = tmp_path / "videos"
    (folder / "sub").mkdir(parents=True)
    first = shutil.copy(short_video, folder / "a.mp4")
    second = shutil.copy(short_video, folder / "sub" / "b.mp4")
    third = shutil.copy(short_video, tmp_path / "c.mp4")
    run("-i", str(folder), str(third), "--angle", "180")
    for f in (first, second, third):
        assert Path(str(f).replace(".mp4", ".r180.mp4")).exists()


def test_command_output_file_with_several_files_is_rejected(short_video: str, tmp_path: Path) -> None:
    """Command output file with several files is rejected"""
    first = shutil.copy(short_video, tmp_path / "a.mp4")
    second = shutil.copy(short_video, tmp_path / "b.mp4")
    with pytest.raises(SystemExit) as e:
        run("-i", str(first), str(second), "-o", str(tmp_path / "out.mp4"))
    assert e.value.code == 2


def test_command_resolution_alias_and_fps(clip: str) -> None:
    """Command resolution alias and fps"""
    run("-i", clip, "--fps", "12", "--resolution", "90x160")
    out = clip.replace("clip.mp4", "clip.r90.mp4")
    assert size(out) == (90, 160)
    assert float(video.VideoFile(out).get_fps()) == 12


def test_rotate_is_a_videotool_action() -> None:
    """Rotate is a videotool action"""
    assert "rotate" in tools.VIDEO_ACTIONS


def test_hw_accel_option_is_available(capsys: pytest.CaptureFixture[str]) -> None:
    """Hw accel option is available"""
    with pytest.raises(SystemExit) as e:
        run("-h")
    assert e.value.code == 0
    assert "--hw_accel" in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["auto", "on", "off"])
def test_hw_accel_option_is_passed_to_the_rotation(clip: str, mode: str) -> None:
    """Hw accel option is passed to the rotation"""
    with patch.object(video, "rotate", return_value=clip) as rotate:
        run("-i", clip, "--hw_accel", mode)
    assert rotate.call_args.kwargs["hw_accel"] == mode


def test_hw_accel_is_auto_by_default(clip: str) -> None:
    """Hw accel is auto by default"""
    with patch.object(video, "rotate", return_value=clip) as rotate:
        run("-i", clip)
    assert rotate.call_args.kwargs["hw_accel"] == "auto"


def test_invalid_hw_accel_option(clip: str) -> None:
    """Invalid hw accel option"""
    with pytest.raises(SystemExit) as e:
        run("-i", clip, "--hw_accel", "maybe")
    assert e.value.code == 2


@pytest.fixture(scope="session")
def codec_clips(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """Short 320x180 videos encoded with h265 and mpeg4"""
    folder = tmp_path_factory.mktemp("codecs")
    clips = {}
    for name, codec in (("h265", "libx265"), ("mpeg4", "mpeg4")):
        path = str(folder / f"{name}.mp4")
        subprocess.run(
            [util.get_ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=25:duration=1", "-c:v", codec, path], check=True
        )
        clips[name] = path
    return clips


def video_codec(file: str) -> str:
    """Returns the video codec of a video file"""
    return video.VideoFile(file).get_video_codec()


def test_rotate_keeps_the_codec_of_the_original_video(codec_clips: dict, tmp_path: Path) -> None:
    """Rotate keeps the codec of the original video"""
    for name, expected in (("h265", "hevc"), ("mpeg4", "h264")):  # mpeg4 is not supported: default codec (h264)
        src = shutil.copy(codec_clips[name], tmp_path / f"{name}.mp4")
        out = video.rotate(str(src), hw_accel="off")
        assert video_codec(out) == expected


def test_rotate_h264_by_default(clip: str) -> None:
    """Rotate h264 by default"""
    assert video_codec(video.rotate(clip, hw_accel="off")) == "h264"


def test_rotate_vcodec_option(codec_clips: dict, clip: str) -> None:
    """Rotate vcodec option"""
    assert video_codec(video.rotate(clip, vcodec="h265", hw_accel="off")) == "hevc"
    assert video_codec(video.rotate(codec_clips["h265"], vcodec="h264", hw_accel="off")) == "h264"


def test_rotate_commands_use_the_original_codec_and_quality(codec_clips: dict) -> None:
    """Rotate commands use the original codec and quality"""
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.rotate(codec_clips["h265"], hw_accel="off")
    cmd = run_ffmpeg.call_args.args[0]
    assert "libx265" in cmd
    assert re.search(r'-crf "?23', cmd)  # x265 high quality
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.rotate(codec_clips["h265"], hw_accel="on")
    cmd = run_ffmpeg.call_args.args[0]
    assert "hevc_nvenc" in cmd
    assert re.search(r'-cq "?23', cmd)


def test_command_vcodec_option(clip: str) -> None:
    """Command vcodec option"""
    run("-i", clip, "--vcodec", "x265", "--hw_accel", "off")
    assert video_codec(clip.replace("clip.mp4", "clip.r90.mp4")) == "hevc"


@pytest.mark.parametrize(("vcodec", "ext", "tagged"), [("h265", "mp4", True), ("h265", "mov", True), ("h264", "mp4", False), ("h265", "mkv", False)])
def test_rotate_tags_hevc_as_hvc1(clip: str, tmp_path: Path, vcodec: str, ext: str, tagged: bool) -> None:
    """HEVC videos in mp4 or mov are tagged hvc1, that Windows Explorer and the video editors need (ffmpeg tags hev1 by default)"""
    with patch.object(util, "run_ffmpeg") as run_ffmpeg:
        video.rotate(clip, str(tmp_path / f"out.{ext}"), vcodec=vcodec, hw_accel="off")
    assert ("-tag:v" in run_ffmpeg.call_args.args[0]) is tagged
    if tagged:
        assert '-tag:v "hvc1"' in run_ffmpeg.call_args.args[0]


def test_rotate_hevc_is_playable_by_the_editors(video_5s: str, tmp_path: Path) -> None:
    """The rotated HEVC video really has the hvc1 tag"""
    out = video.rotate(video_5s, str(tmp_path / "out.mp4"), vcodec="h265", hw_accel="off")
    ffprobe = conf.get_property("binaries.ffprobe") or "ffprobe"
    cmd = [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_tag_string", "-of", "csv=p=0", out]
    assert subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip() == "hvc1"
