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

import os
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
