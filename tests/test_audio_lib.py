#!python3
#
# media-tools
# Copyright (C) 2021 Olivier Korach
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
import platform
import mediatools.utilities as util
import mediatools.audio_lib as ad
import mediatools.file as fil

SONG = "it/song.mp3"
TITLE = 'Love Is Stronger Than Pride'
ARTIST = 'Sade'

def test_changed_drive():
    if platform.system() == "Windows":
        original_file = os.path.abspath(SONG)
        moved_file = "Z" + original_file[1:]
        assert ad.search_on_other_drives(moved_file) == original_file
        moved_file = "Z:\\foo.txt"
        assert ad.search_on_other_drives(moved_file) is None
    else:
        assert True

def test_fix_symlink():
    symlink = "shortcut.lnk"
    util.set_debug_level(5)
    if platform.system() == "Windows":
        original_file = os.path.abspath(SONG)
        moved_file = "Z" + original_file[1:]
        f = fil.File(moved_file)
        f.create_link(symlink)
        assert ad.__fix_symlink(symlink, moved_file) == original_file
        f2 = fil.File(symlink)
        assert f2.read_link() == original_file
    else:
        assert True

def test_fix_symlink_2():
    symlink = "shortcut.lnk"
    if platform.system() == "Windows":
        moved_file = "doesnotexit.txt"
        f = fil.File(moved_file)
        f.create_link(symlink)
        assert ad.__fix_symlink(symlink, moved_file) is None
    else:
        assert True
