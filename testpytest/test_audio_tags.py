
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
import mediatools.audiofile as audio

SONG = "it/song.mp3"
TITLE = 'Love Is Stronger Than Pride'
ARTIST = 'Sade'

def test_tags_all():
    aud = audio.AudioFile(SONG)
    tags = aud.get_tags()
    assert tags['title'] == TITLE
    assert tags['artist'] == ARTIST

def test_tags_v1():
    aud = audio.AudioFile(SONG)
    tags = aud.get_tags_by_version(1)
    assert tags['title'] == TITLE
    assert tags['artist'] == ARTIST

def test_tags_v2():
    aud = audio.AudioFile(SONG)
    tags = aud.get_tags_by_version(2)
    assert tags['title'] == TITLE
    assert tags['artist'] == ARTIST

def test_tags_vall():
    aud = audio.AudioFile(SONG)
    tags = aud.get_tags_by_version()
    assert tags['title'] == TITLE
    assert tags['artist'] == ARTIST
