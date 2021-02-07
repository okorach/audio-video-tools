
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

import os
import mediatools.audiofile as audio
import mediatools.utilities as util

SYMLINK = "it/symlink-song.mp3"
FILE = "it/song.mp3"


def test_symlink_1():
    assert util.is_symlink(SYMLINK) == True
    assert util.is_symlink(FILE) == False


def test_symlink_2():
    file = util.get_symlink_target(SYMLINK)
    assert file == FILE
