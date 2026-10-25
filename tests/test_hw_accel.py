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

"""Tests of the --hw_accel option (auto, on, off) and of the fallback to the CPU when a hardware accelerated command fails"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import subprocess
import sys
from contextlib import AbstractContextManager
from pathlib import Path
from unittest import mock

import pytest

import mediatools.utilities as util
import mediatools.videofile as video
from cli import encode as cli_encode
from mediatools import (
    album_art,
    audio_denoise,
    audioconcat,
    audiospeed,
    audiosplit,
    blindify,
    concat,
    crop,
    crop_ratio,
    cut,
    deshake,
    encode,
    image2video,
    metadata,
    mux,
    poster,
    rescale,
    reverse,
    shake,
    speed,
    stabilize,
    stack,
    tools,
    video_enhance,
    volume,
)

FILE = "it/video-720p.mp4"
HW_COMMAND = "-hwaccel cuda -i in.mp4 -c:v h264_nvenc out.mp4"
CPU_COMMAND = "-i in.mp4 -c:v libx264 out.mp4"


@pytest.fixture
def gpu_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """The check of the availability of the hardware acceleration says it's available"""
    monkeypatch.setattr(util, "HW_ACCEL", True)


@pytest.fixture
def no_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulates a computer without GPU"""
    monkeypatch.setattr(util, "HW_ACCEL", False)


def failing_gpu_commands() -> AbstractContextManager:
    """Replaces the execution of the commands: those using the hardware acceleration fail, the others succeed"""

    def run_os_cmd(cmd: str, duration: float | None = None) -> None:
        """Replaces the execution of the commands: those using the hardware acceleration fail, the others succeed"""
        if util.HW_ACCEL_COMMAND_REGEXP.search(cmd):
            raise subprocess.CalledProcessError(1, cmd, output="Conversion failed!")

    return mock.patch("mediatools.utilities.run_os_cmd", side_effect=run_os_cmd)


# Mode of the hardware acceleration
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "auto"),
        ("auto", "auto"),
        ("on", "on"),
        ("off", "off"),
        ("ON", "on"),
        (" Off ", "off"),
        (True, "on"),
        (False, "off"),
        ("whatever", "auto"),
    ],
)
def test_hw_accel_mode(value: str | bool, expected: str) -> None:
    """Hw accel mode"""
    with mock.patch("mediatools.media_config.get_property", return_value=None):
        assert util.get_hw_accel_mode(hw_accel=value) == expected


def test_hw_accel_mode_default() -> None:
    """Hw accel mode default"""
    with mock.patch("mediatools.media_config.get_property", return_value="off"):
        assert util.get_hw_accel_mode() == "off"
        assert util.get_hw_accel_mode(hw_accel="on") == "on"


def test_use_hardware_accel_explicit(no_gpu: None) -> None:
    """Use hardware accel explicit"""
    assert util.use_hardware_accel(hw_accel="on")
    assert util.use_hardware_accel(hw_accel=True)
    assert not util.use_hardware_accel(hw_accel="off")
    assert not util.use_hardware_accel(hw_accel=False)


def test_use_hardware_accel_auto(gpu_available: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Use hardware accel auto"""
    assert util.use_hardware_accel(hw_accel="auto")
    assert not util.use_hardware_accel(hw_accel="auto", deinterlace=True)
    monkeypatch.setattr(util, "HW_ACCEL", False)
    assert not util.use_hardware_accel(hw_accel="auto")


def test_use_hardware_accel_does_not_change_the_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit mode doesn't alter the result of the check of the availability of the hardware acceleration"""
    monkeypatch.setattr(util, "HW_ACCEL", None)
    util.use_hardware_accel(hw_accel="off")
    util.use_hardware_accel(hw_accel="on")
    assert util.HW_ACCEL is None


def test_check_hardware_accel_is_done_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check hardware accel is done once"""
    monkeypatch.setattr(util, "HW_ACCEL", None)
    with mock.patch("mediatools.utilities.run_ffmpeg") as run, mock.patch("os.remove"):
        assert util.check_hardware_accel()
        assert util.check_hardware_accel()
    assert run.call_count == 1


def test_check_hardware_accel_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check hardware accel failure"""
    monkeypatch.setattr(util, "HW_ACCEL", None)
    with mock.patch("mediatools.utilities.run_ffmpeg", side_effect=subprocess.CalledProcessError(1, "ffmpeg")):
        assert not util.check_hardware_accel()
    assert util.HW_ACCEL is False


# The option of the tools
def test_hw_accel_option_default() -> None:
    """Hw accel option default"""
    parser = util.get_common_args("test", "test")
    with mock.patch("mediatools.media_config.get_property", return_value=None):
        assert util.parse_media_args(parser, ["-i", "a.mp4"])["hw_accel"] == "auto"


@pytest.mark.parametrize("mode", ["auto", "on", "off"])
def test_hw_accel_option_values(mode: str) -> None:
    """Hw accel option values"""
    parser = util.get_common_args("test", "test")
    assert util.parse_media_args(parser, ["-i", "a.mp4", "--hw_accel", mode])["hw_accel"] == mode


def test_hw_accel_option_invalid() -> None:
    """Hw accel option invalid"""
    parser = util.get_common_args("test", "test")
    with pytest.raises(SystemExit) as e:
        util.parse_media_args(parser, ["-i", "a.mp4", "--hw_accel", "maybe"])
    assert e.value.code == 2


TOOLS = [
    album_art,
    audio_denoise,
    audioconcat,
    audiospeed,
    audiosplit,
    blindify,
    concat,
    crop,
    crop_ratio,
    cut,
    deshake,
    encode,
    cli_encode,
    image2video,
    metadata,
    mux,
    poster,
    rescale,
    reverse,
    shake,
    speed,
    stabilize,
    stack,
    video_enhance,
    volume,
]


@pytest.mark.parametrize("tool", TOOLS, ids=[t.__name__ for t in TOOLS])
def test_tools_have_the_hw_accel_option(tool: str, capsys: pytest.CaptureFixture[str]) -> None:
    """All the tools that decode or encode media have the --hw_accel option"""
    command, action = tools.find_action(tool.__name__)
    with mock.patch.object(sys, "argv", [command, action, "-h"]), pytest.raises(SystemExit) as e:
        tools.run(command)
    assert e.value.code == 0
    assert "--hw_accel" in capsys.readouterr().out


@pytest.mark.parametrize("tool", TOOLS, ids=[t.__name__ for t in TOOLS])
def test_tools_refuse_invalid_hw_accel(tool: str) -> None:
    """Tools refuse invalid hw accel"""
    command, action = tools.find_action(tool.__name__)
    with mock.patch.object(sys, "argv", [command, action, "-i", FILE, "--hw_accel", "maybe"]), pytest.raises(SystemExit) as e:
        tools.run(command)
    assert e.value.code == 2


def test_slideshow_option(tmp_path: Path) -> None:
    """Slideshow option"""
    out_file = tmp_path / "o.mp4"
    with (
        mock.patch.object(sys, "argv", ["videotool", "slideshow", "-i", FILE, "--hw_accel", "off", "-o", str(out_file)]),
        mock.patch("mediatools.videofile.slideshow", return_value=(str(out_file), [])) as make_slideshow,
        mock.patch("builtins.open", mock.mock_open()),
        mock.patch("yaml.safe_dump"),
    ):
        tools.videotool()
    assert make_slideshow.call_args.kwargs["hw_accel"] == "off"


def test_slideshow_invalid_option() -> None:
    """Slideshow invalid option"""
    with mock.patch.object(sys, "argv", ["videotool", "slideshow", "-i", FILE, "--hw_accel", "maybe"]), pytest.raises(SystemExit) as e:
        tools.videotool()
    assert e.value.code == 2


def test_concat_passes_the_mode() -> None:
    """Concat passes the mode"""
    with (
        mock.patch.object(sys, "argv", ["videotool", "concat", "-i", FILE, FILE, "-o", "o.mp4", "--hw_accel", "on"]),
        mock.patch("mediatools.videofile.concat", return_value="o.mp4") as concatenate,
    ):
        tools.videotool()
    assert concatenate.call_args.kwargs["hw_accel"] == "on"


# Fallback to the CPU
def test_fallback_retries_on_the_cpu(gpu_available: None) -> None:
    """Fallback retries on the cpu"""
    attempts = []

    @util.hw_accel_fallback
    def convert(hw_accel: str = "auto") -> str:
        """Function that is run with the hardware acceleration, and again on the CPU when it fails with it"""
        attempts.append(util.use_hardware_accel(hw_accel=hw_accel))
        util.run_ffmpeg(HW_COMMAND if attempts[-1] else CPU_COMMAND)
        return "done"

    with failing_gpu_commands():
        assert convert() == "done"
    assert attempts == [True, False]


def test_fallback_with_a_keyword_argument(gpu_available: None) -> None:
    """Fallback with a keyword argument"""
    attempts = []

    @util.hw_accel_fallback
    def convert(*, source: str, **kwargs: object) -> None:
        """Function that is run with the hardware acceleration, and again on the CPU when it fails with it, with the options as keyword arguments"""
        attempts.append(util.use_hardware_accel(**kwargs))
        util.run_ffmpeg(HW_COMMAND if attempts[-1] else CPU_COMMAND)

    with failing_gpu_commands():
        convert(source="a", hw_accel="auto")
    assert attempts == [True, False]


def test_fallback_in_a_method(gpu_available: None) -> None:
    """Fallback in a method"""
    attempts = []

    class Converter:  # pylint: disable=too-few-public-methods
        """Class with a method that is run again on the CPU when it fails with the hardware acceleration"""

        @util.hw_accel_fallback
        def convert(self, target: str, **kwargs: object) -> str:
            """Function that is run with the hardware acceleration, and again on the CPU when it fails with it, as a method"""
            attempts.append(util.use_hardware_accel(**kwargs))
            util.run_ffmpeg(HW_COMMAND if attempts[-1] else CPU_COMMAND)
            return target

    with failing_gpu_commands():
        assert Converter().convert("out.mp4") == "out.mp4"
    assert attempts == [True, False]


def test_no_fallback_when_forced_on(gpu_available: None) -> None:
    """No fallback when forced on"""
    attempts = []

    @util.hw_accel_fallback
    def convert(hw_accel: str = "auto") -> None:
        """Function that runs a command with the hardware acceleration"""
        attempts.append(util.use_hardware_accel(hw_accel=hw_accel))
        util.run_ffmpeg(HW_COMMAND)

    with failing_gpu_commands(), pytest.raises(subprocess.CalledProcessError):
        convert(hw_accel="on")
    assert attempts == [True]


def test_no_hardware_acceleration_when_turned_off(gpu_available: None) -> None:
    """No hardware acceleration when turned off"""
    attempts = []

    @util.hw_accel_fallback
    def convert(hw_accel: str = "auto") -> None:
        """Function that runs a CPU command, recording whether the hardware acceleration was requested"""
        attempts.append(util.use_hardware_accel(hw_accel=hw_accel))
        util.run_ffmpeg(CPU_COMMAND)

    with failing_gpu_commands():
        convert(hw_accel="off")
    assert attempts == [False]


def test_no_retry_without_gpu(no_gpu: None) -> None:
    """No retry without gpu"""
    attempts = []

    @util.hw_accel_fallback
    def convert(hw_accel: str = "auto") -> None:
        """Function that runs a CPU command, recording whether the hardware acceleration was requested and fails"""
        attempts.append(util.use_hardware_accel(hw_accel=hw_accel))
        util.run_ffmpeg(CPU_COMMAND)
        raise subprocess.CalledProcessError(1, "ffmpeg")

    with failing_gpu_commands(), pytest.raises(subprocess.CalledProcessError):
        convert()
    assert attempts == [False]


def test_no_retry_when_the_failed_command_is_not_hardware_accelerated(gpu_available: None) -> None:
    """A failure of a command on the CPU would fail the same way on the CPU: it's not run twice"""
    attempts = []

    @util.hw_accel_fallback
    def convert(hw_accel: str = "auto") -> None:
        """Function that runs a CPU command and fails"""
        attempts.append(1)
        util.run_ffmpeg(CPU_COMMAND)
        raise subprocess.CalledProcessError(1, "ffmpeg")

    with failing_gpu_commands(), pytest.raises(subprocess.CalledProcessError):
        convert()
    assert len(attempts) == 1


def test_failure_on_the_cpu_is_raised(gpu_available: None) -> None:
    """Failure on the cpu is raised"""
    attempts = []

    @util.hw_accel_fallback
    def convert(hw_accel: str = "auto") -> None:
        """Function that runs a command that fails on the CPU, with or without the hardware acceleration"""
        attempts.append(util.use_hardware_accel(hw_accel=hw_accel))
        util.run_ffmpeg(HW_COMMAND if attempts[-1] else CPU_COMMAND)
        if not attempts[-1]:
            raise subprocess.CalledProcessError(1, "ffmpeg")

    with failing_gpu_commands(), pytest.raises(subprocess.CalledProcessError):
        convert()
    assert attempts == [True, False]


def test_other_errors_are_not_retried(gpu_available: None) -> None:
    """Other errors are not retried"""
    attempts = []

    @util.hw_accel_fallback
    def convert(hw_accel: str = "auto") -> None:
        """Function that fails with an error that is not a failure of ffmpeg"""
        attempts.append(1)
        raise ValueError("not an ffmpeg failure")

    with pytest.raises(ValueError, match="not an ffmpeg"):
        convert()
    assert len(attempts) == 1


def test_nested_functions_are_retried_once_by_the_outer_one(gpu_available: None) -> None:
    """Nested functions are retried once by the outer one"""
    inner_calls = []
    outer_calls = []

    @util.hw_accel_fallback
    def inner(hw_accel: str = "auto") -> None:
        """Function that runs a command, called by the outer function"""
        hw = util.use_hardware_accel(hw_accel=hw_accel)
        inner_calls.append(hw)
        util.run_ffmpeg(HW_COMMAND if hw else CPU_COMMAND)

    @util.hw_accel_fallback
    def outer(hw_accel: str = "auto") -> None:
        """Function that calls the inner function and has the fallback"""
        outer_calls.append(util.use_hardware_accel(hw_accel=hw_accel))
        inner(hw_accel=hw_accel)

    with failing_gpu_commands():
        outer()
    assert outer_calls == [True, False]
    assert inner_calls == [True, False]


def test_the_hardware_acceleration_is_used_again_after_a_fallback(gpu_available: None) -> None:
    """The hardware acceleration is used again after a fallback"""

    @util.hw_accel_fallback
    def convert(hw_accel: str = "auto") -> None:
        """Function that runs a command with the hardware acceleration if it is used"""
        util.run_ffmpeg(HW_COMMAND if util.use_hardware_accel(hw_accel=hw_accel) else CPU_COMMAND)

    with failing_gpu_commands():
        convert()
    assert util.use_hardware_accel(hw_accel="auto")


# Fallback of the real operations
def test_encode_falls_back_to_the_cpu(gpu_available: None) -> None:
    """Encode falls back to the cpu"""
    commands = []

    def run_os_cmd(cmd: str, duration: float | None = None) -> None:
        """Replaces the execution of the commands: records them and fails for the ones using the hardware acceleration"""
        commands.append(cmd)
        if util.HW_ACCEL_COMMAND_REGEXP.search(cmd):
            raise subprocess.CalledProcessError(1, cmd)

    with mock.patch("mediatools.utilities.run_os_cmd", side_effect=run_os_cmd):
        video.VideoFile(FILE).encode(target_file="out.mp4", vcodec="h265", resolution="320x180")
    assert len(commands) == 2
    assert "-hwaccel cuda" in commands[0]
    assert "hevc_nvenc" in commands[0]
    assert "-hwaccel" not in commands[1]
    assert "libx265" in commands[1]


def test_encode_does_not_fall_back_when_forced_on(gpu_available: None) -> None:
    """Encode does not fall back when forced on"""
    vf = video.VideoFile(FILE)
    with failing_gpu_commands() as run, pytest.raises(subprocess.CalledProcessError):
        vf.encode(target_file="out.mp4", vcodec="h265", resolution="320x180", hw_accel="on")
    assert run.call_count == 1


def test_crop_falls_back_to_the_cpu(gpu_available: None) -> None:
    """Crop falls back to the cpu"""
    commands = []

    def run_os_cmd(cmd: str, duration: float | None = None) -> None:
        """Replaces the execution of the commands: records them and fails for the ones using the hardware acceleration"""
        commands.append(cmd)
        if util.HW_ACCEL_COMMAND_REGEXP.search(cmd):
            raise subprocess.CalledProcessError(1, cmd)

    with (
        mock.patch("mediatools.utilities.run_os_cmd", side_effect=run_os_cmd),
        mock.patch("mediatools.videofile.get_creation_date", return_value=None),
    ):
        video.VideoFile(FILE).crop(out_file="out.mp4", box="320x180")
    assert len(commands) == 2
    assert "-hwaccel cuda" in commands[0]
    assert "-hwaccel" not in commands[1]


def test_concat_falls_back_to_the_cpu(gpu_available: None, short_video: str, tmp_path: Path) -> None:
    """Concat falls back to the cpu"""
    commands = []

    def run_os_cmd(cmd: str, duration: float | None = None) -> None:
        """Replaces the execution of the commands: records them and fails for the ones using the hardware acceleration"""
        commands.append(cmd)
        if util.HW_ACCEL_COMMAND_REGEXP.search(cmd):
            raise subprocess.CalledProcessError(1, cmd)

    with mock.patch("mediatools.utilities.run_os_cmd", side_effect=run_os_cmd):
        video.concat(str(tmp_path / "out.mp4"), [short_video, short_video])
    assert len(commands) == 2
    assert "-hwaccel cuda" in commands[0]
    assert "libx265" in commands[1]


def test_concat_mode_off_uses_the_cpu(gpu_available: None, short_video: str, tmp_path: Path) -> None:
    """Concat mode off uses the cpu"""
    with mock.patch("mediatools.utilities.run_os_cmd") as run:
        video.concat(str(tmp_path / "out.mp4"), [short_video, short_video], hw_accel="off")
    assert run.call_count == 1
    assert "-hwaccel" not in run.call_args[0][0]


def test_process_input_files_keeps_the_mode(gpu_available: None) -> None:
    """The tools run through process_input_files get the hw_accel option"""
    seen = []
    util.process_input_files({"inputfiles": ["a"], "hw_accel": "off"}, lambda _f, options: seen.append(options["hw_accel"]))
    assert seen == ["off"]


# Videos that the GPU can't decode (H.264 beyond 4096 pixels or 8 bits): they are decoded on the CPU and uploaded to the GPU
def video_with_stream(**stream: object) -> video.VideoFile:
    """Returns a video whose main stream has the properties given (a 1080p h264 stream by default)"""
    vf = video.VideoFile(FILE)
    vf.specs = {"streams": [{"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "pix_fmt": "yuv420p", **stream}]}
    return vf


@pytest.mark.parametrize(
    ("stream", "expected"),
    [
        ({}, True),
        ({"width": 4096}, True),
        ({"width": 5184, "height": 2916}, False),
        ({"width": 2160, "height": 5120}, False),
        ({"pix_fmt": "yuv420p10le"}, False),
        ({"pix_fmt": "yuv422p"}, False),
        ({"codec_name": "hevc", "width": 5184, "height": 2916, "pix_fmt": "yuv420p10le"}, True),
    ],
)
def test_can_hw_decode(stream: dict, expected: bool) -> None:
    """Can hw decode"""
    assert video_with_stream(**stream).can_hw_decode() is expected


def encode_command(vf: video.VideoFile) -> str:
    """Returns the ffmpeg command that encodes a video in h265 with the hardware acceleration, without running it"""
    with mock.patch("mediatools.utilities.run_os_cmd") as run:
        vf.encode(target_file="out.mp4", vcodec="h265", width=1920, hw_accel="on")
    return run.call_args.args[0]


def test_encode_decodes_on_the_gpu_when_possible() -> None:
    """Encode decodes on the gpu when possible"""
    cmd = encode_command(video_with_stream())
    assert "-hwaccel cuda -hwaccel_output_format cuda" in cmd
    assert "scale_cuda=1920:-2" in cmd
    assert "hwupload_cuda" not in cmd


def test_encode_decodes_on_the_cpu_when_the_gpu_cant() -> None:
    """Encode decodes on the cpu when the gpu cant"""
    cmd = encode_command(video_with_stream(width=5184, height=2916))
    assert "-hwaccel" not in cmd
    assert "hwupload_cuda,scale_cuda=1920:-2" in cmd
    assert "hevc_nvenc" in cmd
