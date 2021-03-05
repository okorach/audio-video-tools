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

import mediatools.audiofile as audio
import mediatools.filespecs as spec

FILE = "it/seal.mp3"


def test_1():
    allp = list(set(spec.VIDEO_PROPS + spec.AUDIO_PROPS + spec.IMAGE_PROPS))
    specs = audio.AudioFile(FILE).get_properties()
    csv = spec.__to_csv__(specs, allp)
    assert ',192000,' in csv
    assert 'Seal' in csv
    assert 'Crazy' in csv
    assert 'it/seal.mp3' in csv

def test_2():
    allp = list(set(spec.VIDEO_PROPS + spec.AUDIO_PROPS + spec.IMAGE_PROPS))
    specs = audio.AudioFile(FILE).get_properties()
    std = spec.__to_std__(specs, allp)
    assert 'abitrate            : 187.5 kbits/s' in std
    assert 'duration            : 00:05:57.094' in std
