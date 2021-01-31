
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

import mediatools.resolution as res
import mediatools.exceptions as ex

def test_canonical_1():
    assert res.canonical('720p') == '1280x720'


def test_canonical_2():
    assert res.canonical('1080p') == '1920x1080'


def test_canonical_3():
    assert res.canonical('4k') == '3840x2160'


def test_canonical_4():
    assert res.canonical('4k') == '3840x2160'


def test_multiply():
    x, y = 1000, 200
    r = res.Resolution(x, y)
    r2 = r * 2
    assert r2.width == x * 2
    assert r2.height == y * 2

def test_multiply_by_0():
    r = res.Resolution(300, 17)
    try:
        _ = r * 0
    except ex.NegativeDimensions as e:
        assert e.message == 'width and height must be strictly positive'

def test_multiply_by_negative():
    r = res.Resolution(100, 100)
    try:
        _ = r * -1
    except ex.NegativeDimensions as e:
        assert e.message == 'width and height must be strictly positive'
