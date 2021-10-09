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
import mediatools.utilities as util
import mediatools.imagefile as img
from mediatools import poster

CMD = 'image-poster'
DIR = 'it' + os.sep
IMG1 = DIR + 'img-640x480.jpg'
IMG2 = DIR + 'img-1770x1291.jpg'
IMG3 = DIR + 'img-3000x4000.jpg'
IMG4 = DIR + 'img-3000x1682.jpg'
IMG5 = DIR + 'img-2880x1924.jpg'
IMG6 = DIR + 'img-4000x3000.jpg'
TMP1 = util.get_tmp_file() + '.jpg'

def test_main():
    with patch.object(sys, 'argv', [CMD, '-g', '4', '-b', 'black', '-m', '10', '--stretch',
                      '-i', IMG1, IMG2, IMG3, IMG4, IMG5, IMG6]):
        try:
            poster.main()
            assert True
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_help():
    with patch.object(sys, 'argv', [CMD, '-i', IMG1, IMG2, '-h']):
        try:
            poster.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_bad_option():
    with patch.object(sys, 'argv', [CMD, '-b', '-i', IMG1, IMG2, '--badoption', 'yes']):
        try:
            poster.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2


def test_main_no_file():
    with patch.object(sys, 'argv', [CMD, '-g', '4', '-b', 'black', '-m', '10']):
        try:
            poster.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2


def test_main_other_options():
    with patch.object(sys, 'argv', [CMD, '-b', 'white', '-m', '50', '-i', IMG1, IMG2]):
        try:
            poster.main()
            assert True
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_with_output():
    with patch.object(sys, 'argv', [CMD, '-g', '2', '-i', IMG1, IMG2, '-o', TMP1]):
        try:
            poster.main()
            assert img.ImageFile(TMP1).width > 0
            os.remove(TMP1)
        except SystemExit as e:
            assert int(str(e)) == 0
            assert img.ImageFile(TMP1).width > 0
            os.remove(TMP1)


def test_main_with_output2():
    with patch.object(sys, 'argv', [CMD, '-g', '2', '-i', IMG1, IMG2, '-b', 'white', '-m', '50', '-o', TMP1]):
        try:
            poster.main()
            assert img.ImageFile(TMP1).width > 0
            os.remove(TMP1)
        except SystemExit as e:
            assert int(str(e)) == 0
            assert img.ImageFile(TMP1).width > 0
            os.remove(TMP1)
