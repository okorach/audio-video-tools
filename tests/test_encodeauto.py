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

"""Tests of encodeauto, with ffmpeg replaced by a function that creates the output file"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import re
import sys
from pathlib import Path
from unittest import mock

import pytest

from mediatools import tools
from mediatools import encodeauto as ea


class Commands(list):
    """The (parameters, duration) of the ffmpeg commands that were run, with the mocks that replace the video functions"""

    def __init__(self) -> None:
        super().__init__()
        self.get_duration = mock.Mock(return_value=7.0)
        self.set_creation_date = mock.Mock()


@pytest.fixture
def fake_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> Commands:
    """ffmpeg creates the output file (the last quoted argument) with the content 'encoded'"""
    commands = Commands()

    def run_ffmpeg(params: str, duration: float | None = None) -> None:
        commands.append((params, duration))
        Path(re.findall(r'"([^"]+)"', params)[-1]).write_text("encoded", encoding="utf-8")

    monkeypatch.setattr(ea.util, "run_ffmpeg", run_ffmpeg)
    monkeypatch.setattr(ea.video, "get_duration", commands.get_duration)
    monkeypatch.setattr(ea.video, "get_creation_date", mock.Mock(return_value="THE-DATE"))
    monkeypatch.setattr(ea.video, "set_creation_date", commands.set_creation_date)
    return commands


def names(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir())


def test_encode_file_replaces_the_file_and_keeps_the_original(fake_ffmpeg: Commands, tmp_path: Path) -> None:
    src = tmp_path / "clip.mp4"
    src.write_text("original")
    ea.encode_file(str(src), "-hwaccel cuda", "-c:v hevc_nvenc", True)
    assert names(tmp_path) == ["clip.mp4", "clip.original.mp4"]
    assert src.read_text() == "encoded"
    assert (tmp_path / "clip.original.mp4").read_text() == "original"
    params, duration = fake_ffmpeg[0]
    assert params.startswith('-hwaccel cuda -i "')
    assert "-c:v hevc_nvenc" in params
    assert params.endswith('clip.encode.00.mp4"')
    assert duration == 7.0
    fake_ffmpeg.set_creation_date.assert_called_once_with(str(tmp_path / "clip.encode.00.mp4"), "THE-DATE")


def test_encode_file_given_duration(fake_ffmpeg: Commands, tmp_path: Path) -> None:
    src = tmp_path / "clip.mp4"
    src.write_text("original")
    ea.encode_file(str(src), "", "", True, duration=99.0)
    assert fake_ffmpeg[0][1] == 99.0
    fake_ffmpeg.get_duration.assert_not_called()


def test_encode_file_does_not_overwrite_encoded_files(fake_ffmpeg: Commands, tmp_path: Path) -> None:
    """Without force, the output file name gets the next sequence number"""
    src = tmp_path / "clip.mp4"
    src.write_text("original")
    (tmp_path / "clip.encode.00.mp4").write_text("a previous encoding")
    (tmp_path / "clip.encode.01.mp4").write_text("a previous encoding")
    ea.encode_file(str(src), "", "", False)
    assert fake_ffmpeg[0][0].endswith('clip.encode.02.mp4"')


def test_encode_file_of_an_original_file(fake_ffmpeg: Commands, tmp_path: Path) -> None:
    """The encoded version of clip.original.mp4 is named clip.mp4"""
    src = tmp_path / "clip.original.mp4"
    src.write_text("original")
    ea.encode_file(str(src), "", "", True)
    assert names(tmp_path) == ["clip.mp4", "clip.original.mp4"]
    assert (tmp_path / "clip.mp4").read_text() == "encoded"
    assert src.read_text() == "original"


@pytest.mark.parametrize("extension", ["mts", "avi", "mkv"])
def test_encode_file_converts_to_mp4_and_deinterlaces(fake_ffmpeg: Commands, tmp_path: Path, extension: str) -> None:
    src = tmp_path / f"clip.{extension}"
    src.write_text("original")
    ea.encode_file(str(src), "", "-c:a aac", True)
    assert "-vf yadif_cuda=deint=all -c:a aac" in fake_ffmpeg[0][0]
    assert names(tmp_path) == sorted(["clip.mp4", f"clip.{extension}"])
    assert (tmp_path / "clip.mp4").read_text() == "encoded"
    assert src.read_text() == "original"


# Command line
@pytest.fixture
def cli(monkeypatch: pytest.MonkeyPatch) -> mock.Mock:
    monkeypatch.setattr(ea, "encode_file", mock.Mock())
    monkeypatch.setattr(ea.video, "get_duration", mock.Mock(side_effect=lambda f: 10.0 if "long" in f else 5.0))
    return ea.encode_file


def run_main(*args: str) -> None:
    with mock.patch.object(sys, "argv", ["videotool", "encodeauto", *args]):
        tools.videotool()


def test_main_encodes_each_video_file(cli: mock.Mock, tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    for name in ("a.mp4", "sub/b.mkv", "notes.txt", "pic.jpg"):
        (tmp_path / name).write_text("x")
    run_main("-i", str(tmp_path), "--before", "-y -hwaccel cuda", "--after", "-c:v hevc_nvenc")
    files = [Path(c.args[0]).name for c in cli.call_args_list]
    assert files == ["a.mp4", "b.mkv"]  # Only the video files of the directory
    first = cli.call_args_list[0]
    assert first.args[1:4] == ("-y -hwaccel cuda", "-c:v hevc_nvenc", True)


def test_main_nooverwrite(cli: mock.Mock) -> None:
    run_main("-i", "a.mp4", "--nooverwrite", "--before", " ", "--after", "-an -sn")
    assert cli.call_args.args[3] is False


def test_main_remaining_duration(cli: mock.Mock) -> None:
    run_main("-i", "short.mp4", "long.mp4", "--before", " ", "--after", "-an -sn")
    assert [c.kwargs["duration"] for c in cli.call_args_list] == [15.0, 10.0]


def test_main_without_video_file(cli: mock.Mock, tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("x")
    run_main("-i", str(tmp_path), "--before", " ", "--after", "-an -sn")
    cli.assert_not_called()
