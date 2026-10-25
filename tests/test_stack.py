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
from mediatools import tools
import mediatools.utilities as util
import mediatools.imagefile as img

IMG1 = "it" + os.sep + "img-640x480.jpg"
IMG2 = "it" + os.sep + "img-1770x1291.jpg"
TMP1 = util.get_tmp_file() + ".jpg"


def test_main() -> None:
    with patch.object(sys, "argv", ["imagetool", "stack", "-g", "4", "-b", "black", "-m", "10", "--stretch", "-d", "vertical", "-i", IMG1, IMG2]):
        try:
            tools.imagetool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_help() -> None:
    with patch.object(sys, "argv", ["imagetool", "stack", "-b", "black", "-m", "10", "--stretch", "-d", "vertical", "-i", IMG1, IMG2, "-h"]):
        try:
            tools.imagetool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_bad_option() -> None:
    with patch.object(sys, "argv", ["imagetool", "stack", "-b", "black", "-m", "10", "--badoption", "foo", "-i", IMG1, IMG2]):
        try:
            tools.imagetool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2


def test_main_no_file() -> None:
    with patch.object(sys, "argv", ["imagetool", "stack", "-g", "4", "-b", "black", "-m", "10"]):
        try:
            tools.imagetool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2


def test_main_other_options() -> None:
    with patch.object(sys, "argv", ["imagetool", "stack", "-b", "white", "-m", "50", "-d", "horizontal", "-i", IMG1, IMG2]):
        try:
            tools.imagetool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_with_output() -> None:
    with patch.object(sys, "argv", ["imagetool", "stack", "-g", "2", "-i", IMG1, IMG2, "-o", TMP1]):
        try:
            tools.imagetool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0
            assert img.ImageFile(TMP1).width > 0
            os.remove(TMP1)


def test_main_with_output2() -> None:
    with patch.object(sys, "argv", ["imagetool", "stack", "-g", "2", "-i", IMG1, IMG2, "-b", "white", "-m", "50", "-d", "horizontal", "-o", TMP1]):
        try:
            tools.imagetool()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0
            assert img.ImageFile(TMP1).width > 0
            os.remove(TMP1)
