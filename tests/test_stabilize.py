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

"""Tests of video-stabilize, with ffmpeg mocked"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import os
import platform
import re
import sys
from unittest import mock

import pytest

from mediatools import tools
from mediatools import stabilize as stab
from collections.abc import Iterator


def completed(stdout: str = "", stderr: str = "") -> mock.Mock:
    """Returns a mock of the result of a command"""
    return mock.Mock(stdout=stdout, stderr=stderr)


def test_has_vidstab() -> None:
    """Has vidstab"""
    with mock.patch("subprocess.run", return_value=completed(stdout=" ... vidstabdetect  V->V ...")):
        assert stab.has_vidstab()


def test_has_vidstab_in_stderr() -> None:
    """Has vidstab in stderr"""
    with mock.patch("subprocess.run", return_value=completed(stderr="vidstabdetect")):
        assert stab.has_vidstab()


def test_has_no_vidstab() -> None:
    """Has no vidstab"""
    with mock.patch("subprocess.run", return_value=completed(stdout="scale  V->V")):
        assert not stab.has_vidstab()


def test_has_vidstab_without_ffmpeg() -> None:
    """Has vidstab without ffmpeg"""
    with mock.patch("subprocess.run", side_effect=FileNotFoundError):
        assert not stab.has_vidstab()


def test_run_vidstabdetect() -> None:
    """Run vidstabdetect"""
    with mock.patch("mediatools.utilities.run_ffmpeg") as run:
        trf = stab.run_vidstabdetect("clip.mp4", shakiness=5)
    try:
        assert trf.endswith(".trf")
        params = run.call_args.args[0]
        assert params.startswith('-i "clip.mp4" -vf "vidstabdetect=shakiness=5:accuracy=15:result=')
        assert trf in params
        assert params.endswith('-f null "NUL"' if platform.system() == "Windows" else '-f null "/dev/null"')
    finally:
        os.unlink(trf)


def test_stabilize_two_passes() -> None:
    """Stabilize two passes"""
    with mock.patch.object(stab, "has_vidstab", return_value=True), mock.patch("mediatools.utilities.run_ffmpeg") as run:
        output = stab.stabilize("dir/clip.mp4", smoothing=10, zoom=5, optzoom=2)
    assert output == os.path.join("dir", "clip.stabilized.mp4") or output.endswith("clip.stabilized.mp4")
    assert run.call_count == 2
    detect, transform = (c.args[0] for c in run.call_args_list)
    assert "vidstabdetect=shakiness=8" in detect
    assert "vidstabtransform=smoothing=10:optzoom=2:zoom=5:input=" in transform
    assert ",unsharp=5:5:0.8:3:3:0.4" in transform
    assert transform.endswith(f'"{output}"')
    trf = re.search(r"result='([^']+)'", detect).group(1)
    assert not os.path.exists(trf)  # The transforms file is removed


def test_stabilize_without_sharpening_to_the_given_output() -> None:
    """Stabilize without sharpening to the given output"""
    with mock.patch.object(stab, "has_vidstab", return_value=True), mock.patch("mediatools.utilities.run_ffmpeg") as run:
        output = stab.stabilize("clip.mp4", output="out.mp4", sharpen=False)
    assert output == "out.mp4"
    assert "unsharp" not in run.call_args_list[1].args[0]


def test_stabilize_removes_the_transforms_file_on_failure() -> None:
    """Stabilize removes the transforms file on failure"""
    with (
        mock.patch.object(stab, "has_vidstab", return_value=True),
        mock.patch("mediatools.utilities.run_ffmpeg", side_effect=[None, RuntimeError("boom")]) as run,
        pytest.raises(RuntimeError),
    ):
        stab.stabilize("clip.mp4")
    trf = re.search(r"result='([^']+)'", run.call_args_list[0].args[0]).group(1)
    assert not os.path.exists(trf)


def test_stabilize_falls_back_to_deshake_without_vidstab() -> None:
    """Stabilize falls back to deshake without vidstab"""
    with mock.patch.object(stab, "has_vidstab", return_value=False), mock.patch.object(stab.video, "VideoFile") as video_file:
        video_file.return_value.encode.return_value = "deshaken.mp4"
        assert stab.stabilize("clip.mp4", output="out.mp4") == "deshaken.mp4"
    video_file.assert_called_once_with("clip.mp4")
    kwargs = video_file.return_value.encode.call_args.kwargs
    assert kwargs["target_file"] == "out.mp4"
    assert kwargs["deshake"] == "32x32"
    assert kwargs["hw_accel"] is False


# Command line
@pytest.fixture
def cli() -> Iterator[mock.MagicMock]:
    """Replaces the stabilization of a video. Returns the mock of the stabilization"""
    with (
        mock.patch.object(stab, "stabilize", side_effect=lambda f, output=None, **_kw: output or f + ".stabilized") as stabilize,
        mock.patch("mediatools.utilities.generated_file"),
    ):
        yield stabilize


def run_main(*args: str) -> None:
    """Runs the command with the arguments given"""
    with mock.patch.object(sys, "argv", ["videotool", "stabilize", *args]):
        tools.videotool()


def test_main_defaults(cli: mock.MagicMock) -> None:
    """Main defaults"""
    run_main("-i", "a.mp4")
    cli.assert_called_once_with("a.mp4", output=None, shakiness=8, smoothing=30, zoom=0, optzoom=1, sharpen=True)


def test_main_options(cli: mock.MagicMock) -> None:
    """Main options"""
    run_main("-i", "a.mp4", "-o", "out.mp4", "--shakiness", "3", "--smoothing", "12", "--zoom", "4", "--optzoom", "0", "--no-sharpen")
    cli.assert_called_once_with("a.mp4", output="out.mp4", shakiness=3, smoothing=12, zoom=4, optzoom=0, sharpen=False)


def test_main_several_files_ignore_the_output_name(cli: mock.MagicMock) -> None:
    """With several files, the name of each output is derived from its input"""
    run_main("-i", "a.mp4", "b.mp4", "-o", "out.mp4")
    assert [(c.args[0], c.kwargs["output"]) for c in cli.call_args_list] == [("a.mp4", None), ("b.mp4", None)]
