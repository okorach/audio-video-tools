
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
import tempfile
import mediatools.imagefile as image
import mediatools.videofile as video
import mediatools.exceptions as ex

EX_PAN_DURATION_POSITIVE = "panorama: duration must be a strictly positive number"
TMP_VID = tempfile.gettempdir() + os.sep + next(tempfile._get_candidate_names()) + '.mp4'
TMP_IMG = tempfile.gettempdir() + os.sep + next(tempfile._get_candidate_names()) + '.jpg'

def get_img(w, h, orientation='landscape'):
    small_img = image.__get_background__('black')
    portrait_img = image.ImageFile(image.ImageFile(small_img).scale(w, h, out_file=TMP_IMG))
    portrait_img.orientation = orientation
    return portrait_img


def test_pan_input_4():
    large_img = get_img(4000, 3000)
    try:
        _ = large_img.panorama(duration=-5, speed=0.1, out_file=TMP_VID)
        os.remove(TMP_VID)
        assert False
    except ex.InputError as e:
        assert e.message == EX_PAN_DURATION_POSITIVE
    finally:
        os.remove(large_img.filename)


def test_pan_input_5():
    large_img = get_img(4000, 3000)
    try:
        _ = large_img.panorama(duration=0, speed=0.1, out_file=TMP_VID)
        os.remove(TMP_VID)
        assert False
    except ex.InputError as e:
        assert e.message == EX_PAN_DURATION_POSITIVE
    finally:
        os.remove(large_img.filename)


def test_pan_1():
    img = get_img(4000, 3000)
    (vid, _) = img.panorama(duration=5, speed="10%", resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 5
    os.remove(vid)
    os.remove(img.filename)


def test_pan_2():
    img = get_img(4000, 3000)
    (vid, _) = img.panorama(effect=(0, 1, 0.5, 0.5), speed="10%", resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 10
    os.remove(vid)
    os.remove(img.filename)


def test_pan_3():
    img = get_img(4000, 3000)
    (vid, _) = img.panorama(effect=(0, 1, 0.5, 0.5), duration=5, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 5
    os.remove(vid)
    os.remove(img.filename)


def test_pan_4():
    img = get_img(4000, 3000)
    (vid, _) = img.panorama(effect=(1, 0, 0.5, 0.5), speed=0.2, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 5
    os.remove(vid)
    os.remove(img.filename)


def test_pan_5():
    img = get_img(4000, 3000)
    (vid, _) = img.to_video(with_effect=False, duration=3, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 3
    os.remove(vid)
    os.remove(img.filename)


def test_pan_6():
    img = get_img(4000, 3000)
    (vid, _) = img.panorama(duration=3, speed=0.2, vspeed=0.1, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 3
    os.remove(vid)
    os.remove(img.filename)


def test_pan_portrait():
    img = get_img(3000, 4000, 'portrait')
    (vid, _) = img.panorama(duration=3, speed=0.2, vspeed=0.1, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 3
    os.remove(vid)
    os.remove(img.filename)
