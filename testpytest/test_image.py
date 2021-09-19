
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
import mediatools.exceptions as ex
import mediatools.imagefile as image
import mediatools.videofile as video

TMP_VID = tempfile.gettempdir() + os.sep + next(tempfile._get_candidate_names()) + '.mp4'

def get_img(w, h, orientation='landscape'):
    img = image.ImageFile(image.get_rectangle('black', w, h))
    img.probe()
    img.orientation = orientation
    return img

def del_files(*imgs):
    for o in imgs:
        os.remove(o.filename)

def test_str():
    img = get_img(400, 300)
    s = str(img)
    print("STR = %s" % s)
    assert "'width': 400" in s
    assert "'filename': '{}'".format(img.filename) in s
    del_files(img)

def test_scale_1():
    w, h = 400, 200
    img = get_img(w, h)
    assert img.resolution.width == w
    assert img.resolution.height == h
    del_files(img)

def test_needed_frame_1():
    w, h = 4000, 3000
    img = get_img(w, h)
    (_, tot_w, tot_h) = img.__compute_total_frame__(6000, 3500)
    assert tot_w == 6000
    assert tot_h == 4500
    del_files(img)


def test_needed_frame_2():
    w, h = 4000, 3000
    img = get_img(w, h)
    (_, tot_w, tot_h) = img.__compute_total_frame__(5000, 4500)
    assert tot_w == 6000
    assert tot_h == 4500
    del_files(img)

def test_needed_frame_3():
    w, h = 4000, 3000
    img = get_img(w, h)
    (_, tot_w, tot_h) = img.__compute_total_frame__(3000, 3600)
    assert tot_w == 4800
    assert tot_h == 3600
    del_files(img)

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
    w, h = 3000, 2000
    img = get_img(w, h)
    (vid_o, _) = video.VideoFile(img.to_video(with_effect=True, duration=3, speed=0.02, out_file=TMP_VID))
    assert vid_o.duration == 3
    del_files(img, vid_o)

def test_to_image_still():
    w, h = 2000, 2000
    img = get_img(w, h)
    (vid_o, _) = video.VideoFile(img.to_video(with_effect=False, duration=3, out_file=TMP_VID))
    assert vid_o.duration == 3
    del_files(img, vid_o)

def test_widths_and_heights():
    w, h = 4000, 3000
    img = get_img(w, h)
    pt = get_img(w, h, orientation='portrait')
    widths = image.get_widths([img.filename, pt.filename, img.filename])
    assert widths == [4000, 4000, 4000]
    assert image.avg_width([img.filename, pt.filename, img.filename, pt.filename]) == 4000
    heights = image.get_heights([img.filename, pt.filename, img.filename])
    assert heights == [3000, 3000, 3000]
    assert image.avg_height([img.filename, pt.filename, pt.filename, pt.filename]) == 3000
    del_files(img, pt)

def test_properties():
    w, h = 3000, 2000
    img = get_img(w, h)
    props = img.get_properties()
    assert props['format'] == 'mjpeg'
    assert props['width'] == 3000
    props = img.get_image_properties()
    assert props['format'] == 'mjpeg'
    assert props['height'] == 2000
    del_files(img)

def test_dimensions_2():
    w, h = 4000, 3000
    img = get_img(w, h, orientation='portrait')
    (w, h) = img.dimensions(ignore_orientation=False)
    assert w == 3000
    assert h == 4000
    del_files(img)

def test_crop():
    w, h = 4000, 3000
    img = get_img(w, h, orientation='portrait')
    f = image.ImageFile(img.crop(position='center-top', width=3500, height=2000))
    assert f.width == 3500 and f.height == 2000
    del_files(img, f)

def test_scale():
    w, h = 4000, 3000
    img = get_img(w, h)
    f = image.ImageFile(img.scale(w=2000))
    assert f.width == 2000 and f.height == 1500
    f = image.ImageFile(img.scale(h=6000))
    assert f.width == 8000 and f.height == 6000
    del_files(img, f)


def test_no_scale():
    w, h = 4000, 3000
    img = get_img(w, h)
    f = image.ImageFile(img.scale())
    assert f.width == 4000 and f.height == 3000
    del_files(img, f)

def test_blindify():
    w, h = 4000, 3000
    img = get_img(w, h)
    f = image.ImageFile(img.blindify(blinds=5, direction='vertical', blinds_size=50))
    assert f.width == 4200
    f = image.ImageFile(img.blindify(blinds=10, direction='horizontal', blinds_size='1%'))
    assert f.height == 3810
    del_files(img, f)

def test_shake_1():
    w, h = 1000, 200
    img = get_img(w, h)
    # util.set_debug_level(5)
    f = image.ImageFile(img.shake(nbr_slices=20, direction='vertical', shake_pct=5))
    assert f.height == 210
    del_files(img, f)

def test_shake_2():
    w, h = 1000, 200
    img = get_img(w, h)
    f = image.ImageFile(img.shake(nbr_slices=20, direction='horizontal', shake_pct=10))
    assert f.width == 1100
    del_files(img, f)


def test_rotate():
    w, h = 4000, 3000
    img = get_img(w, h, orientation='portrait')
    f = image.ImageFile(img.rotate())
    assert f.width == 3000 and f.height == 4000
    try:
        image.ImageFile(img.rotate(degrees=180))
        assert False
    except ex.InputError:
        assert True
    except Exception:
        assert False
    finally:
        del_files(img, f)
