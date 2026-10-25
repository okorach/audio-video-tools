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

import os
import re
import platform
import utilities.file as fil
import mediatools.videofile as video
from mediatools import version
from pathlib import Path

BASE = "video-720p.mp4"
FILE = "it" + os.sep + BASE
FILE_2 = "it" + os.sep + "video-1920x1080.mp4"
FILE_SIZE = 2001067


def test_file_std() -> None:
    f = fil.File(FILE)
    assert f.stat()
    assert f.size() == FILE_SIZE


def test_file_video() -> None:
    f = video.VideoFile(FILE)
    assert f.stat()
    assert f.size() == FILE_SIZE


def test_file_unexisting() -> None:
    f = fil.File("nonexist.txt")
    assert not f.stat()


def test_extension() -> None:
    assert fil.extension(FILE) == "mp4"
    f = fil.File(FILE)
    assert f.extension() == "mp4"


def test_basename() -> None:
    assert fil.basename(FILE, strip_ext=False) == BASE
    assert fil.basename(FILE) == "video-720p"
    assert fil.basename(FILE, strip_dir=False, strip_ext=False) == os.path.abspath(FILE)
    f = fil.File(FILE)
    assert f.basename(strip_ext=False) == BASE
    assert f.basename() == "video-720p"


def test_dirname() -> None:
    # The directory of a file is returned as an absolute path (with the drive letter on Windows)
    dirname = os.path.abspath(os.sep.join(["", "usr", "local", "bin"]))
    filename = dirname + os.sep + "python3"
    assert fil.dirname(filename) == dirname
    f = fil.File(filename)
    assert f.dirname() == dirname


def test_link(tmp_path: Path) -> None:
    assert not fil.is_link(FILE)
    assert not fil.is_shortcut(FILE)
    f = fil.File(FILE)
    assert not f.is_link()
    assert not f.is_shortcut()
    lnk = f.create_link(str(tmp_path / "link_to_video"))
    assert fil.is_link(lnk)

    # The link points to the absolute path of the file
    target = os.path.normcase(os.path.abspath(FILE))
    obj = fil.File(lnk)
    assert obj.is_link()
    if platform.system() == "Windows":
        assert obj.is_shortcut()
    else:
        assert not obj.is_shortcut()
    assert os.path.normcase(obj.read_link()) == target
    assert os.path.normcase(fil.read_link(lnk)) == target


def test_hash() -> None:
    f = fil.File("nonexisting")
    assert f.hash() is None
    f = fil.File(FILE)
    assert f.hash() is not None


def test_hash_list() -> None:
    hashes = fil.get_hash_list([FILE, FILE_2, FILE])
    h = next(iter(hashes))
    assert h is not None
    assert len(hashes[h]) == 2
    print(str(hashes))
    assert list(hashes.keys())[1] is not None
    assert len(hashes.keys()) == 2


def test_version() -> None:
    assert re.match(r"^[0-9.]+$", version.MEDIA_TOOLS_VERSION)
