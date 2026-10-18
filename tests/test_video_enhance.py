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

"""Tests of video-enhance, with the ffmpeg commands and the file operations mocked"""

import sys
import types
from pathlib import Path
from unittest import mock

import pytest

from mediatools import video_enhance as ve


@pytest.fixture
def collab(monkeypatch, tmp_path):
    """Replaces everything enhance_file() calls: the video functions, the stabilization and the file operations"""
    trf = tmp_path / "detected.trf"

    def detect(_filename):
        trf.write_text("trf")
        return str(trf)

    mocks = types.SimpleNamespace(
        trf=trf,
        get_creation_date=mock.Mock(return_value="THE-DATE"),
        set_creation_date=mock.Mock(),
        color_enhance=mock.Mock(return_value="enhanced.mp4"),
        has_vidstab=mock.Mock(return_value=True),
        run_vidstabdetect=mock.Mock(side_effect=detect),
        rename=mock.Mock(),
        generated_file=mock.Mock(),
    )
    monkeypatch.setattr(ve.video, "get_creation_date", mocks.get_creation_date)
    monkeypatch.setattr(ve.video, "set_creation_date", mocks.set_creation_date)
    monkeypatch.setattr(ve.video, "color_enhance", mocks.color_enhance)
    monkeypatch.setattr(ve.stab, "has_vidstab", mocks.has_vidstab)
    monkeypatch.setattr(ve.stab, "run_vidstabdetect", mocks.run_vidstabdetect)
    monkeypatch.setattr(ve.fileutil, "rename", mocks.rename)
    monkeypatch.setattr(ve.util, "generated_file", mocks.generated_file)
    return mocks


def enhance(**kwargs):
    ve.enhance_file("dir/clip.mp4", kwargs.pop("output_file", None), 1.3, 1.1, 0.0, 1.0, **kwargs)


def test_enhance_replaces_the_file_and_keeps_the_original(collab):
    enhance()
    kwargs = collab.color_enhance.call_args.kwargs
    assert collab.color_enhance.call_args.args == ("dir/clip.mp4", None)
    assert (kwargs["saturation"], kwargs["contrast"], kwargs["brightness"], kwargs["gamma"]) == (1.3, 1.1, 0.0, 1.0)
    collab.set_creation_date.assert_called_once_with("enhanced.mp4", "THE-DATE")
    assert [c.args for c in collab.rename.call_args_list] == [("dir/clip.mp4", "dir/clip.original.mp4"), ("enhanced.mp4", "dir/clip.mp4")]
    collab.generated_file.assert_called_once_with("dir/clip.mp4")


def test_enhance_with_output_file_keeps_the_input(collab):
    enhance(output_file="out.mp4")
    assert collab.color_enhance.call_args.args == ("dir/clip.mp4", "out.mp4")
    collab.rename.assert_not_called()
    collab.generated_file.assert_called_once_with("enhanced.mp4")


def test_enhance_stabilizes_with_vidstab(collab):
    enhance()
    kwargs = collab.color_enhance.call_args.kwargs
    assert kwargs["vidstab_trf"] == str(collab.trf)
    assert "deshake" not in kwargs
    assert not collab.trf.exists()  # The transforms file is removed


def test_enhance_falls_back_to_deshake_without_vidstab(collab):
    collab.has_vidstab.return_value = False
    enhance()
    kwargs = collab.color_enhance.call_args.kwargs
    assert kwargs["deshake"] == "32x32"
    assert "vidstab_trf" not in kwargs
    collab.run_vidstabdetect.assert_not_called()


def test_enhance_continues_if_the_motion_detection_fails(collab):
    collab.run_vidstabdetect.side_effect = RuntimeError("boom")
    enhance()
    kwargs = collab.color_enhance.call_args.kwargs
    assert "vidstab_trf" not in kwargs
    assert "deshake" not in kwargs
    collab.generated_file.assert_called_once()


def test_enhance_without_stabilization(collab):
    enhance(stabilize=False)
    collab.has_vidstab.assert_not_called()
    collab.run_vidstabdetect.assert_not_called()
    kwargs = collab.color_enhance.call_args.kwargs
    assert "vidstab_trf" not in kwargs
    assert "deshake" not in kwargs


def test_enhance_passes_hw_accel_and_batch_remaining(collab):
    enhance(hw_accel=False, batch_remaining=42.5, stabilize=False)
    kwargs = collab.color_enhance.call_args.kwargs
    assert kwargs["hw_accel"] is False
    assert kwargs["batch_remaining"] == 42.5  # noqa: PLR2004


def test_enhance_does_not_pass_unset_options(collab):
    enhance(stabilize=False)
    kwargs = collab.color_enhance.call_args.kwargs
    assert "hw_accel" not in kwargs
    assert "batch_remaining" not in kwargs


def test_enhance_failure_leaves_the_files_untouched(collab):
    collab.color_enhance.side_effect = RuntimeError("ffmpeg failed")
    enhance()
    collab.rename.assert_not_called()
    collab.set_creation_date.assert_not_called()
    collab.generated_file.assert_not_called()
    assert not collab.trf.exists()  # The transforms file is removed in any case


# Command line
@pytest.fixture
def cli(monkeypatch):
    enhance_file = mock.Mock()
    monkeypatch.setattr(ve, "enhance_file", enhance_file)
    monkeypatch.setattr(ve.video, "get_duration", mock.Mock(side_effect=lambda f: 10.0 if "long" in f else 5.0))
    return enhance_file


def run_main(*args: str) -> None:
    with mock.patch.object(sys, "argv", ["video-enhance", *args]):
        ve.main()


def test_main_defaults(cli):
    run_main("-i", "a.mp4")
    assert cli.call_count == 1
    assert cli.call_args.args == ("a.mp4", None, 1.3, 1.1, 0.0, 1.0)
    assert cli.call_args.kwargs["hw_accel"] is False
    assert cli.call_args.kwargs["stabilize"] is True
    assert cli.call_args.kwargs["batch_remaining"] == 5.0  # noqa: PLR2004


def test_main_options(cli):
    run_main(
        "-i",
        "a.mp4",
        "--saturation",
        "2",
        "--contrast",
        "1.5",
        "--brightness",
        "0.1",
        "--gamma",
        "2",
        "--gpu_filters",
        "--no_stabilize",
        "-o",
        "o.mp4",
    )
    assert cli.call_args.args == ("a.mp4", "o.mp4", 2.0, 1.5, 0.1, 2.0)
    assert cli.call_args.kwargs["hw_accel"] is None  # GPU filters: the hardware acceleration is left to the auto mode
    assert cli.call_args.kwargs["stabilize"] is False


def test_main_remaining_duration_of_the_batch(cli):
    run_main("-i", "short.mp4", "long.mp4")
    assert [c.kwargs["batch_remaining"] for c in cli.call_args_list] == [15.0, 10.0]


def test_main_skips_generated_files(cli):
    run_main("-i", "a.mp4", str(Path("dir") / "a.color.mp4"), "a.original.mp4")
    assert [c.args[0] for c in cli.call_args_list] == ["a.mp4"]


def test_main_only_generated_files(cli):
    run_main("-i", "a.color.mp4")
    cli.assert_not_called()


def test_main_output_file_with_several_files(cli):
    run_main("-i", "a.mp4", "b.mp4", "-o", "o.mp4")
    cli.assert_not_called()
