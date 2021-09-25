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
import sys
from unittest.mock import patch
from mediatools import stack


images = (
    "it" + os.sep + "img-1770x1291.jpg", "it" + os.sep + "img-3000x4000.jpg", "it" + os.sep + "img-640x480.jpg"
)


def test_main():
    file1 = 'it' + os.sep + 'img-640x480.jpg'
    file2 = 'it' + os.sep + 'img-1770x1291.jpg'
    with patch.object(sys, 'argv', ['image-stack', '-g', '4', '-b', 'black', '-m', '10', '--stretch', '-d', 'vertical', file1, file2]):
        try:
            stack.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0

def test_main_help():
    file1 = 'it' + os.sep + 'img-640x480.jpg'
    file2 = 'it' + os.sep + 'img-1770x1291.jpg'
    with patch.object(sys, 'argv', ['image-stack', '-g', '4', '-b', 'black', '-m', '10', '--stretch', '-d', 'vertical', file1, file2, '-h']):
        try:
            stack.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_no_file():
    with patch.object(sys, 'argv', ['image-stack', '-g', '4', '-b', 'black', '-m', '10', '--stretch', '-d', 'vertical']):
        try:
            stack.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 1


def test_main_other_options():
    file1 = 'it' + os.sep + 'img-640x480.jpg'
    file2 = 'it' + os.sep + 'img-1770x1291.jpg'
    with patch.object(sys, 'argv', ['image-stack', '-b', 'white', '-m', '50', '-d', 'horizontal', file1, file2]):
        try:
            stack.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0
