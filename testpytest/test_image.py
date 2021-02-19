
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
import mediatools.imagefile as image
import mediatools.videofile as video

TMP_VID = "/tmp/vid.mp4"
TMP2 = '/tmp/file2.jpg'
LARGE_LANDSCAPE = "/tmp/large.jpg"
LARGE_PORTRAIT = "/tmp/portrait.jpg"

large_img = None
portrait_img = None


def get_large_img(w, h):
    global large_img
    if large_img is not None:
        return large_img

    small_img = image.__get_background__('black')
    large_file = image.ImageFile(small_img).scale(w, h, out_file="/tmp/large.jpg")
    large_img = image.ImageFile(large_file)
    return large_img


def get_portrait_img(w, h):
    global portrait_img
    if portrait_img is not None:
        return portrait_img

    small_img = image.__get_background__('black')
    large_file = image.ImageFile(small_img).scale(w, h, out_file="/tmp/portrait.jpg")
    portrait_img = image.ImageFile(large_file)
    portrait_img.orientation = 'portrait'
    return portrait_img


def del_large_img():
    global large_img
    os.remove(large_img.filename)
    large_img = None


def test_scale_1():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    assert large_img.resolution.width == w
    assert large_img.resolution.height == h


def test_needed_frame_1():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    (_, tot_w, tot_h) = large_img.__compute_total_frame__(6000, 3500)
    assert tot_w == 6000
    assert tot_h == 4500

def test_properties():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    props = large_img.get_properties()
    assert props['format'] == 'mjpeg'
    assert props['width'] == 4000
    props = large_img.get_image_properties()
    assert props['format'] == 'mjpeg'
    assert props['height'] == 3000

def test_dimensions_2():
    w, h = 4000, 3000
    large_img = get_portrait_img(w, h)
    (w, h) = large_img.dimensions(ignore_orientation=False)
    assert w == 3000
    assert h == 4000

def test_crop():
    w, h = 4000, 3000
    large_img = get_portrait_img(w, h)
    f = image.ImageFile(large_img.crop(out_file=TMP2, position='center-top', width=3500, height=2000))
    assert f.width == 3500
    assert f.height == 2000
    os.remove(TMP2)

def test_scale():
    w, h = 4000, 3000
    large_img = get_portrait_img(w, h)
    f = image.ImageFile(large_img.scale(out_file=TMP2), w=2000)
    assert f.width == 2000
    assert f.height == 1500
    f = image.ImageFile(large_img.scale(out_file=TMP2), h=6000)
    assert f.width == 8000
    assert f.height == 6000
    os.remove(TMP2)

def test_no_scale():
    w, h = 4000, 3000
    large_img = get_portrait_img(w, h)
    f = image.ImageFile(large_img.scale(out_file=TMP2))
    assert f.width == 4000
    assert f.height == 3000
    os.remove(TMP2)

def test_blindify():
    w, h = 4000, 3000
    large_img = get_portrait_img(w, h)
    f = image.ImageFile(large_img.blindify(out_file=TMP2, blinds=4, direction='vertical', blinds_size=50))
    assert f.width == 4200
    f = image.ImageFile(large_img.blindify(out_file=TMP2, blinds=10, direction='horizontal', blinds_size='1%'))
    assert f.height == 3300
    os.remove(TMP2)

def test_rotate():
    w, h = 4000, 3000
    large_img = get_portrait_img(w, h)
    f = image.ImageFile(large_img.rotate(out_file=TMP2))
    assert f.width == 3000
    assert f.height == 4000
    f = image.ImageFile(large_img.rotate(out_file=TMP2, degrees=180))
    assert f.width == 4000
    assert f.width == 3000
    os.remove(TMP2)


def test_str():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    s = str(large_img)
    assert '"filename": "/tmp/large.jpg"' in s
    assert '"width": 4000' in s


def test_needed_frame_2():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    (_, tot_w, tot_h) = large_img.__compute_total_frame__(5000, 4500)
    assert tot_w == 6000
    assert tot_h == 4500


def test_needed_frame_3():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    (_, tot_w, tot_h) = large_img.__compute_total_frame__(3000, 3600)
    assert tot_w == 4800
    assert tot_h == 3600

def test_type():
    try:
        _ = image.ImageFile('it/seal.mp3')
        assert False
    except ex.FileTypeError:
        assert True
    try:
        _ = image.ImageFile('it/video-720p.mp4')
        assert False
    except ex.FileTypeError:
        assert True

def test_to_image_effect():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    large_img.to_video(with_effect=True, duration=3, speed=0.02, out_file=TMP_VID)
    vid_o = video.VideoFile(TMP_VID)
    assert vid_o.duration == 3

def test_to_image_still():
    w, h = 4000, 3000
    large_img = get_large_img(w, h)
    large_img.to_video(with_effect=False, duration=3, out_file=TMP_VID)
    vid_o = video.VideoFile(TMP_VID)
    assert vid_o.duration == 3

def test_widths_and_heights():
    w, h = 4000, 3000
    img = get_large_img(w, h)
    pt = get_portrait_img(w, h)
    widths = image.get_widths(img.filename, pt.filename, LARGE_LANDSCAPE)
    assert widths == [4000, 3000, 4000]
    assert image.avg_width(img.filename, pt.filename, LARGE_LANDSCAPE, LARGE_PORTRAIT) == 3500
    heights = image.get_heights(img.filename, pt.filename, LARGE_LANDSCAPE)
    assert heights == [3000, 4000, 3000]
    assert image.avg_height(img.filename, pt.filename, LARGE_PORTRAIT, LARGE_PORTRAIT) == 3250
