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
from mediatools import concat
import mediatools.utilities as util
import mediatools.videofile as video

CMD = 'video-concat'
VIDEO1 = 'it' + os.sep + 'video-720p.mp4'
VIDEO2 = 'it' + os.sep + 'video-1920x1080.mp4'
TMP1 = util.get_tmp_file() + '.mp4'
TMP2 = util.get_tmp_file() + '.mp4'
TMP3 = util.get_tmp_file() + '.mp4'


def test_main_with_output():
    util.HW_ACCEL = False
    v1 = video.VideoFile(VIDEO1).encode(profile='360p', target_file=TMP1)
    v2 = video.VideoFile(VIDEO2).encode(profile='360p', target_file=TMP2)
    with patch.object(sys, 'argv', [CMD, '-g', '3', '-i', v1, v2, '-o', TMP3]):
        try:
            concat.main()
            assert abs(video.VideoFile(v1).duration + video.VideoFile(v2).duration -
                       video.VideoFile(TMP3).duration) < 0.06
        except SystemExit as e:
            assert int(str(e)) == 0
            assert abs(video.VideoFile(v1).duration + video.VideoFile(v2).duration -
                       video.VideoFile(TMP3).duration) < 0.06


def test_main_help():
    with patch.object(sys, 'argv', [CMD, '-h']):
        try:
            concat.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0


def test_main_bad_option():
    with patch.object(sys, 'argv', [CMD, '-i', VIDEO1, '--badoption', 'yes']):
        try:
            concat.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2


def test_main_no_file():
    with patch.object(sys, 'argv', [CMD, '-o', TMP1]):
        try:
            concat.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2
