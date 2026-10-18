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

"""Tests of the renamer file renaming logic"""

import datetime
import os
import sys
from unittest import mock

from mediatools import renamer


def _make(tmp_path, **files) -> dict[str, str]:
    paths = {}
    for name, content in files.items():
        p = tmp_path / f"{name}.txt"
        p.write_text(content)
        paths[name] = str(p)
    return paths


def _content(tmp_path) -> dict[str, str]:
    return {f.name: f.read_text() for f in tmp_path.iterdir()}


def test_simple_rename(tmp_path):
    p = _make(tmp_path, a="A")
    assert renamer.rename_files([(p["a"], str(tmp_path / "z.txt"))])
    assert _content(tmp_path) == {"z.txt": "A"}


def test_swap(tmp_path):
    p = _make(tmp_path, a="A", b="B")
    assert renamer.rename_files([(p["a"], p["b"]), (p["b"], p["a"])])
    assert _content(tmp_path) == {"a.txt": "B", "b.txt": "A"}


def test_chain_conflict(tmp_path):
    p = _make(tmp_path, a="A", b="B", c="C")
    assert renamer.rename_files([(p["a"], p["b"]), (p["b"], p["c"]), (p["c"], str(tmp_path / "d.txt"))])
    assert _content(tmp_path) == {"b.txt": "A", "c.txt": "B", "d.txt": "C"}


def test_no_op_rename(tmp_path):
    p = _make(tmp_path, a="A")
    assert renamer.rename_files([(p["a"], p["a"])])
    assert _content(tmp_path) == {"a.txt": "A"}


def test_duplicate_targets_get_suffix(tmp_path):
    p = _make(tmp_path, a="A", b="B")
    target = str(tmp_path / "x.txt")
    assert renamer.rename_files([(p["a"], target), (p["b"], target)])
    assert _content(tmp_path) == {"x.txt": "A", "x 2.txt": "B"}


def test_existing_file_outside_batch_not_overwritten(tmp_path):
    p = _make(tmp_path, a="A", other="O")
    assert renamer.rename_files([(p["a"], p["other"])])
    assert _content(tmp_path) == {"other.txt": "O", "other 2.txt": "A"}


def test_failure_restores_original_names(tmp_path):
    p = _make(tmp_path, a="A", b="B", c="C")
    real_rename = os.rename
    calls = []

    def flaky(src, dst):
        calls.append((src, dst))
        if len(calls) == 5:  # fails during the second phase
            raise OSError("boom")
        real_rename(src, dst)

    with mock.patch("mediatools.renamer.os.rename", side_effect=flaky):
        assert not renamer.rename_files([(p["a"], p["b"]), (p["b"], p["c"]), (p["c"], p["a"])])
    assert _content(tmp_path) == {"a.txt": "A", "b.txt": "B", "c.txt": "C"}


def test_failure_in_first_phase_restores_original_names(tmp_path):
    p = _make(tmp_path, a="A", b="B")
    real_rename = os.rename
    calls = []

    def flaky(src, dst):
        calls.append((src, dst))
        if len(calls) == 2:
            raise OSError("boom")
        real_rename(src, dst)

    with mock.patch("mediatools.renamer.os.rename", side_effect=flaky):
        assert not renamer.rename_files([(p["a"], p["b"]), (p["b"], p["a"])])
    assert _content(tmp_path) == {"a.txt": "A", "b.txt": "B"}


def test_time_placeholder(tmp_path):
    """#TIME# is replaced by the time of day only, as HHhMMmSSs"""
    src = tmp_path / "a.mp4"
    src.write_text("a")
    data = {
        "x": {
            "file": str(src),
            "filename": "a.mp4",
            "device": "Cam",
            "size": "10x20",
            "fps": 25,
            "bitrate": 5,
            "creation_date": datetime.datetime(2024, 3, 9, 14, 5, 7),
        }
    }
    argv = ["renamer", "-i", str(src), "--video_format", "#SEQ2# - #TIME# - #DEVICE#"]
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch("mediatools.renamer.get_files_data", return_value=data),
        mock.patch("mediatools.renamer.rename_files", return_value=True) as rename,
    ):
        renamer.main()
    renames = rename.call_args[0][0]
    assert renames == [(str(src), str(tmp_path / "01 - 14h05m07s - Cam.mp4"))]


def test_time_placeholder_has_no_sequence_prefix():
    """A format containing #TIME# is used as is: no sequence prefix is added"""
    assert renamer.get_fmt("a.mp4", "x", "DJI_#TIME#", "x") == "DJI_#TIME#"
    assert renamer.get_fmt("a.jpg", "DJI_#TIME#", "x", "x") == "DJI_#TIME#"
    assert renamer.get_fmt("a.txt", "x", "x", "DJI_#TIME#") == "DJI_#TIME#"
    # Formats without date, time or sequence still get the sequence prefix
    assert renamer.get_fmt("a.mp4", "x", "DJI", "x") == "#SEQ# - DJI"


def _file_data(path, creation_date: datetime.datetime) -> dict:
    return {
        "file": str(path),
        "filename": os.path.basename(str(path)),
        "device": "Cam",
        "size": "10x20",
        "fps": 25,
        "bitrate": 5,
        "creation_date": creation_date,
    }


def _run_main(tmp_path, names: list[str], dates: list[datetime.datetime], *args: str) -> list[tuple[str, str]]:
    files = []
    data = {}
    for i, (name, date) in enumerate(zip(names, dates, strict=True)):
        f = tmp_path / name
        f.write_text(name)
        files.append(str(f))
        data[f"{date:%Y%m%d%H%M%S} {i:06}"] = _file_data(f, date)
    argv = ["renamer", "-i", *files, *args]
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch("mediatools.renamer.get_files_data", return_value=data),
        mock.patch("mediatools.renamer.rename_files", return_value=True) as rename,
    ):
        renamer.main()
    return rename.call_args[0][0]


def test_time_placeholder_each_file_uses_its_own_time(tmp_path):
    """Each file gets the time of its own creation date"""
    dates = [datetime.datetime(2024, 3, 9, 8, 0, 1), datetime.datetime(2024, 3, 9, 23, 59, 59)]
    renames = _run_main(tmp_path, ["a.mp4", "b.mp4"], dates, "--video_format", "#SEQ2# #TIME#")
    assert [os.path.basename(new) for _, new in renames] == ["01 08h00m01s.mp4", "02 23h59m59s.mp4"]


def test_time_placeholder_photos_and_prefix(tmp_path):
    """#TIME# works in photo formats and in the format built from --prefix"""
    renames = _run_main(tmp_path, ["a.jpg"], [datetime.datetime(2024, 3, 9, 1, 2, 3)], "--photo_format", "#TIME# - #SIZE#")
    assert os.path.basename(renames[0][1]) == "01h02m03s - 10x20.jpg"
    renames = _run_main(tmp_path, ["b.jpg"], [datetime.datetime(2024, 3, 9, 1, 2, 3)], "--prefix", "Trip #TIME#")
    assert "Trip 01h02m03s" in os.path.basename(renames[0][1])


def test_time_placeholder_with_timestamp(tmp_path):
    """#TIME# and #TIMESTAMP# can be used together"""
    renames = _run_main(tmp_path, ["a.mp4"], [datetime.datetime(2024, 3, 9, 14, 5, 7)], "--video_format", "#TIMESTAMP# (#TIME#)")
    assert os.path.basename(renames[0][1]) == "2024-03-09 14h05m07s (14h05m07s).mp4"


def test_time_placeholder_no_prefix_in_file_name(tmp_path):
    """DJI_#TIME# gives DJI_14h05m07s, without sequence prefix"""
    renames = _run_main(tmp_path, ["a.mp4"], [datetime.datetime(2024, 3, 9, 14, 5, 7)], "--video_format", "DJI_#TIME#")
    assert os.path.basename(renames[0][1]) == "DJI_14h05m07s.mp4"
