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
import shutil
import mediatools.exceptions as ex
import mediatools.utilities as util
import mediatools.videofile as video

FILE = 'it/video-720p.mp4'
TMP1 = '/tmp/vid1.mp4'
TMP2 = "/tmp/vid2.mp4"

def test_type():
    try:
        _ = video.VideoFile('it/seal.mp3')
        assert False
    except ex.FileTypeError:
        assert True
    except Exception:
        assert False

    try:
        _ = video.VideoFile('it/img-640x480.jpg')
        assert False
    except ex.FileTypeError:
        assert True
    except Exception:
        assert False

    try:
        _ = video.VideoFile(FILE)
        assert True
    except Exception:
        assert False

def test_video_specs():
    v = video.VideoFile(FILE)
    v.probe()
    specs = v.get_video_specs()
    assert specs['streams'][0]['width'] == 1280
    assert specs['streams'][0]['codec_name'] == 'h264'

def test_attributes():
    v = video.VideoFile(FILE)
    assert v.get_aspect_ratio() == '16:9'
    v = video.VideoFile(FILE)
    assert v.get_pixel_aspect_ratio() == '1:1'
    v = video.VideoFile(FILE)
    assert v.get_duration() == 10
    v = video.VideoFile(FILE)
    assert v.dimensions() == (1280, 720)
    v = video.VideoFile(FILE)
    assert v.get_width() == 1280
    v = video.VideoFile(FILE)
    assert v.get_height() == 720
    v = video.VideoFile(FILE)
    assert str(v.get_resolution()) == '1280x720'
    v = video.VideoFile(FILE)
    p = v.get_video_properties()
    assert p['file_size'] == 2001067

    v = video.VideoFile(FILE)
    p = v.get_properties()
    assert p['vbitrate'] == 1489365

def test_crop():
    v = video.VideoFile(FILE)
    cropv = video.VideoFile(v.crop(out_file=TMP1, width=160, height=160, position='center'))
    cropv.probe()
    assert cropv.aspect == '1:1'

def test_add_metadata():
    shutil.copy(FILE, TMP1)
    v = video.VideoFile(TMP1)
    util.set_debug_level(5)
    outf = v.add_metadata(author='John Doe', year='2027', copyright='JDoe Corp', default_track=0, language=['0:fr:Croatian'])
    v2 = video.VideoFile(outf)
    v2.get_video_specs()
    # assert v2.author == 'John Doe'
    # assert v2.year == 2027
    assert v2.copyright == "© JDoe Corp"
    os.remove(TMP1)
    os.remove(v2.filename)

def test_speed():
    v1 = video.VideoFile(FILE)
    v2 = video.VideoFile(video.speed(FILE, 2, output=TMP1))
    assert v1.duration == 2 * v2.duration
    os.remove(v2.filename)

def test_volume():
    v1 = video.VideoFile(FILE)
    v2 = video.VideoFile(video.volume(FILE, 2, output=TMP1))
    assert v1.duration == v2.duration
    os.remove(v2.filename)

def test_reverse():
    v1 = video.VideoFile(FILE)
    v2 = video.VideoFile(video.reverse(FILE, output=TMP1))
    assert v1.duration == v2.duration
    os.remove(v2.filename)

def test_cut():
    util.set_debug_level(5)
    v = video.VideoFile(video.cut(FILE, output=TMP1, start=0.5, stop=1.5))
    assert abs(1 - v.duration) <= 0.05
    v = video.VideoFile(video.cut(FILE, output=TMP1, timeranges='00:00-00:02'))
    assert abs(2 - v.duration) <= 0.05
