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
import mediatools.exceptions as ex
import mediatools.utilities as util
import mediatools.avfile as av
import mediatools.audiofile as audio
import mediatools.file as fil

AUDIO_FILE = "it" + os.sep + "seal.mp3"
H1 = "Seal-Crazy-Seal-1991-03-357.093878-mp3"
AUDIO_FILE_2 = "it" + os.sep + "ub40.mp3"
H2 = "UB40-I got you babe-The best of UB40-1987-14-190.119184-mp3"
TMP = util.get_tmp_file() + '.mp3'

def test_hash():
    f = audio.AudioFile(AUDIO_FILE)
    f.get_specs()
    assert f.hash() == H1


def test_hash_list():
    l = [AUDIO_FILE, AUDIO_FILE_2, AUDIO_FILE]
    hashes = audio.get_hash_list(l)
    assert list(hashes.keys())[0] == H1
    assert len(hashes[H1]) == 2
    assert list(hashes.keys())[1] == H2
    assert len(hashes.keys()) == 2


def test_tags():
    f = audio.AudioFile(AUDIO_FILE)
    f.get_specs()
    assert f.artist == 'Seal'
    assert f.title == 'Crazy'
    assert f.album == 'Seal'
    assert f.year == 1991
    assert f.genre == 'Pop'


def test_type():
    try:
        _ = audio.AudioFile('it/img-2320x4000.jpg')
        assert False
    except ex.FileTypeError:
        assert True
    try:
        _ = audio.AudioFile('it/video-720p.mp4')
        assert False
    except ex.FileTypeError:
        assert True


def test_cut():
    util.set_debug_level(4)
    start, stop = 12, 19
    v = audio.AudioFile(av.cut(AUDIO_FILE, output=TMP, start=start, stop=stop))
    assert abs(stop - start - v.duration) <= 0.06
    os.remove(v.filename)

def test_cut2():
    util.set_debug_level(4)
    dur = 10
    v = audio.AudioFile(av.cut(AUDIO_FILE, output=TMP, stop=dur))
    assert abs(dur - v.duration) <= 0.06
    os.remove(v.filename)

def test_cut3():
    util.set_debug_level(4)
    v = audio.AudioFile(av.cut(AUDIO_FILE, output=TMP, timeranges='00:10-00:20'))
    assert abs(10 - v.duration) <= 0.06
    os.remove(v.filename)

def test_hash_list_2():
    h_file = "h.json"
    filelist = fil.dir_list("it", recurse=True)
    hash = audio.get_hash_list(filelist)
    audio.save_hash_list(h_file, ".", hash)
    new_hash = audio.read_hash_list(h_file)
    os.remove(h_file)
    assert new_hash == hash
