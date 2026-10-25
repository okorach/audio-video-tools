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

"""Tests of the audio collections linker"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import sys
from pathlib import Path
from unittest import mock

import pytest

from mediatools import linker

HASHES = {"datetime": "2020-01-01 00:00:00", "hashes": {}, "files": {}, "root_directory": ""}


@pytest.fixture
def collection(tmp_path: Path) -> mock.MagicMock:
    """Replaces the hashes and the link and copy functions of the linker (the signatures of the functions are checked).
    Returns the mocks by name"""
    (tmp_path / "master.json").write_text("{}", encoding="utf-8")
    mocks = mock.MagicMock()
    with (
        mock.patch.object(linker.audio, "read_hash_list", return_value=HASHES),
        mock.patch.object(linker.audio, "update_hash_list", mocks.update_hash_list),
        mock.patch.object(linker.fil, "dir_list", return_value=["a.mp3", "b.mp3"]),
        mock.patch.object(linker, "link_file", autospec=True) as mocks.link_file,
        mock.patch.object(linker, "copy_file", autospec=True) as mocks.copy_file,
    ):
        mocks.master = str(tmp_path / "master")
        yield mocks


def run(collection: mock.MagicMock, *args: str) -> int | str | None:
    """Runs the linker on the collection mocks with the arguments given and returns its exit code"""
    with mock.patch.object(sys, "argv", ["audio-linker", "-m", collection.master, "-d", "collection", *args]), pytest.raises(SystemExit) as e:
        linker.main()
    return e.value.code


def test_link_files(collection: mock.MagicMock) -> None:
    """Link files"""
    assert run(collection, "--linkFiles") == 0
    assert collection.link_file.call_args_list == [mock.call("a.mp3", "collection", HASHES), mock.call("b.mp3", "collection", HASHES)]
    collection.copy_file.assert_not_called()


def test_copy_files(collection: mock.MagicMock) -> None:
    """Copy files"""
    assert run(collection, "--copyFiles") == 0
    assert collection.copy_file.call_args_list == [mock.call("a.mp3", "collection"), mock.call("b.mp3", "collection")]
    collection.link_file.assert_not_called()


def test_all(collection: mock.MagicMock) -> None:
    """All: the files are linked and copied"""
    assert run(collection, "--all") == 0
    assert collection.link_file.call_count == 2
    assert collection.copy_file.call_args_list == [mock.call("a.mp3", "collection"), mock.call("b.mp3", "collection")]


def test_update_hash(collection: mock.MagicMock) -> None:
    """Update hash: the hashes of the master directory are rebuilt and nothing else is done"""
    assert run(collection, "--updateHash") == 0
    collection.update_hash_list.assert_called_once_with(collection.master)
    collection.link_file.assert_not_called()
    collection.copy_file.assert_not_called()
