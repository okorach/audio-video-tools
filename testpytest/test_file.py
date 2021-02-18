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
import mediatools.file as fil
import mediatools.videofile as video

FILE = 'it/video-720p.mp4'
FILE_2 = 'it/video-1920x1080.mp4'
FILE_SIZE = 2001067

def test_file_std():
    f = fil.File(FILE)
    assert f.probe()
    assert f.probe()
    assert f.size == FILE_SIZE

def test_file_video():
    f = video.VideoFile(FILE)
    assert f.probe()
    assert f.size == FILE_SIZE

def test_file_unexisting():
    f = fil.File('/tmp/nonexist.txt')
    assert not f.probe()

def test_extension():
    assert fil.extension(FILE) == 'mp4'
    f = fil.File(FILE)
    assert f.extension() == 'mp4'

def test_basename():
    assert fil.basename(FILE) == 'video-720p.mp4'
    assert fil.basename(FILE, 'mp4') == 'video-720p'
    f = fil.File(FILE)
    assert f.basename() == 'video-720p.mp4'
    assert f.basename('mp4') == 'video-720p'

def test_dirname():
    assert fil.dirname('/usr/local/bin/python3') == '/usr/local/bin'
    f = fil.File('/usr/local/bin/python3')
    assert f.dirname() == '/usr/local/bin'

def test_link():
    assert not fil.is_link(FILE)
    assert not fil.is_shortcut(FILE)
    f = fil.File(FILE)
    assert not f.is_link()
    assert not f.is_shortcut()
    lnk = f.create_link("link_to_video")
    assert fil.is_link(lnk)

    obj = fil.File(lnk)
    assert obj.is_link()
    assert not obj.is_shortcut()

    assert obj.read_link() == FILE
    assert fil.read_link(lnk) == FILE

    os.remove(lnk)

def test_hash():
    f = fil.File("/tmp/nonexisting")
    assert f.hash() is None
    f = fil.File(FILE)
    assert f.hash() is not None


def test_hash_list():
    l = [FILE, FILE_2, FILE]
    hashes = fil.get_hash_list(l)
    h = list(hashes.keys())[0]
    assert h is not None
    assert len(hashes[h]) == 2
    assert list(hashes.keys())[1] is not None
    assert len(hashes.keys()) == 2
