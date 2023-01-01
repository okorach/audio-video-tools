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
from mediatools import cut
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.audiofile as audio

CMD = 'media-cut'
VIDEO = 'it' + os.sep + 'video-720p.mp4'
AUDIO = 'it' + os.sep + 'seal.mp3'
TMPV = util.get_tmp_file() + '.mp4'
TMPA = util.get_tmp_file() + '.mp3'

def test_main_v():
    with patch.object(sys, 'argv', [CMD, '--start', '10', '--stop', '20', '-i', VIDEO]):
        cut.main()
        assert True


def test_main_a():
    with patch.object(sys, 'argv', [CMD, '--start', '10', '--stop', '20', '-i', AUDIO]):
        cut.main()
        assert True

def test_main_v_with_output():
    start, stop = 3, 7
    with patch.object(sys, 'argv', [CMD, '--start', str(start), '--stop', str(stop), '-i', VIDEO, '-o', TMPV]):
        cut.main()
        v = video.VideoFile(TMPV)
        v.get_specs()
        assert abs(v.duration + start - stop) < 0.06
        os.remove(TMPV)

def test_main_a_with_output():
    start, stop = 30, 60
    with patch.object(sys, 'argv', [CMD, '--start', str(start), '--stop', str(stop), '-i', AUDIO, '-o', TMPA]):
        cut.main()
        audiofile = audio.AudioFile(TMPA)
        audiofile.get_specs()
        assert abs(audiofile.duration + start - stop) < 0.06
        os.remove(TMPA)

def test_main_help():
    with patch.object(sys, 'argv', [CMD, '-h']):
        try:
            cut.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 0

def test_main_bad_option():
    with patch.object(sys, 'argv', [CMD, '-i', VIDEO, '--badoption', 'yes']):
        try:
            cut.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2

def test_main_no_file():
    with patch.object(sys, 'argv', [CMD, '-o', TMPA]):
        try:
            cut.main()
            assert False
        except SystemExit as e:
            assert int(str(e)) == 2
