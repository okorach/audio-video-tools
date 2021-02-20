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

import mediatools.filters as fil
import mediatools.exceptions as ex

ROTATE = 'rotate: '

def test_rotate_1():
    assert fil.rotate(90) == 'transpose=1'

def test_rotate_2():
    assert fil.rotate(-90) == 'transpose=2'

def test_rotate_3():
    assert fil.rotate(1) == 'transpose=1'

def test_rotate_err_1():
    try:
        _ = fil.rotate(17)
    except ex.InputError as e:
        assert e.message == ROTATE + fil.ERR_ROTATION_ARG_2

def test_rotate_err_2():
    try:
        _ = fil.rotate('counterclockwise')
    except ex.InputError as e:
        assert e.message == ROTATE + fil.ERR_ROTATION_ARG_1

def test_rotate_err_3():
    try:
        _ = fil.rotate(1.5)
    except ex.InputError as e:
        assert e.message == ROTATE + fil.ERR_ROTATION_ARG_3

def test_rotate_err_4():
    try:
        _ = fil.rotate([2])
    except ex.InputError as e:
        assert e.message == ROTATE + fil.ERR_ROTATION_ARG_3

def test_str():
    testf = fil.Simple()
    assert str(testf) == ''
    f = fil.rotate(90)
    testf = fil.Simple(filters=f)
    assert str(testf) == '-vf "{}"'.format(f)
    testf.append(f)
    assert str(testf) == '-vf "{},{}"'.format(f,f)
    o = fil.overlay()
    testf.insert(1, o)
    assert str(testf) == '-vf "{},{},{}"'.format(f,o,f)
    
    testf = fil.Simple(filters=[f,f])
    assert str(testf) == '-vf "{},{}"'.format(f,f)
