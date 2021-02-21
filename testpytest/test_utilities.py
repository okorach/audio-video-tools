
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
import mediatools.utilities as util


def test_conf():
    assert util.get_conf_property('image.default.format') == 'jpg'

def test_hms():
    assert util.to_hms('3727.21') == (1, 2, 7.21)
    assert util.to_hms('7227.33', fmt='string') == "02:00:27.330"
    assert util.to_hms('notfloat') == (0, 0, 0)
    assert util.to_hms('notfloat', fmt='string') == "00:00:00"

def test_to_seconds():
    assert util.to_seconds("02:00:07.327") == 7207.327
    assert util.to_seconds("02:19.111") == 139.111
    assert util.to_seconds("319.111") == 319.111

def test_profile():
    assert util.get_profile_extension(None) == 'mp4'
    assert util.get_profile_extension('mp3_128k') == 'mp3'
    assert util.get_profile_extension('nonexisting') == 'mp4'

def test_generated():
    util.generated_file("foo.txt")
    assert True
