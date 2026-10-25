#
# media-tools
# Copyright (C) 2019-2026 Olivier Korach
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
import mediatools.utilities as util
import mediatools.imagefile as image
import mediatools.videofile as video
import mediatools.exceptions as ex

EX_PAN_DURATION_POSITIVE = "panorama: duration must be a strictly positive number"
TMP_VID = util.get_tmp_file() + ".mp4"
TMP_IMG = util.get_tmp_file() + ".jpg"


# The panorama is slow with large images: the tests use images 5 times smaller than the size they are named after
IMAGE_SCALE_DOWN = 5


def get_img(w: int, h: int, orientation: str = "landscape") -> image.ImageFile:
    """Returns an image of a width and a height, with an orientation, made from a small image"""
    small_img = image.__get_background__("black")
    portrait_img = image.ImageFile(image.ImageFile(small_img).scale(w // IMAGE_SCALE_DOWN, h // IMAGE_SCALE_DOWN, out_file=TMP_IMG))
    portrait_img.orientation = orientation
    return portrait_img


def test_pan_input_4() -> None:
    """Pan input 4"""
    large_img = get_img(4000, 3000)
    try:
        _ = large_img.panorama(duration=-5, speed=0.1, out_file=TMP_VID)
        os.remove(TMP_VID)
        assert False
    except ex.InputError as e:
        assert e.message == EX_PAN_DURATION_POSITIVE
    finally:
        os.remove(large_img.filename)


def test_pan_input_5() -> None:
    """Pan input 5"""
    large_img = get_img(4000, 3000)
    try:
        _ = large_img.panorama(duration=0, speed=0.1, out_file=TMP_VID)
        os.remove(TMP_VID)
        assert False
    except ex.InputError as e:
        assert e.message == EX_PAN_DURATION_POSITIVE
    finally:
        os.remove(large_img.filename)


def test_pan_1() -> None:
    """Pan 1"""
    img = get_img(4000, 3000)
    vid, _ = img.panorama(duration=5, speed="10%", resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 5
    os.remove(vid)
    os.remove(img.filename)


def test_pan_2() -> None:
    """Pan 2"""
    img = get_img(4000, 3000)
    vid, _ = img.panorama(effect=(0, 1, 0.5, 0.5), speed="10%", resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert (vid_o.duration - 5) < 0.1
    os.remove(vid)
    os.remove(img.filename)


def test_pan_3() -> None:
    """Pan 3"""
    img = get_img(4000, 3000)
    vid, _ = img.panorama(effect=(0, 1, 0.5, 0.5), duration=5, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 5
    os.remove(vid)
    os.remove(img.filename)


def test_pan_4() -> None:
    """Pan 4"""
    img = get_img(4000, 3000)
    vid, _ = img.panorama(effect=(1, 0, 0.5, 0.5), speed=0.2, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 5
    os.remove(vid)
    os.remove(img.filename)


def test_pan_5() -> None:
    """Pan 5"""
    img = get_img(4000, 3000)
    vid, _ = img.to_video(with_effect=False, duration=3, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 3
    os.remove(vid)
    os.remove(img.filename)


def test_pan_6() -> None:
    """Pan 6"""
    img = get_img(4000, 3000)
    vid, _ = img.panorama(duration=3, speed=0.2, vspeed=0.1, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 3
    os.remove(vid)
    os.remove(img.filename)


def test_pan_portrait() -> None:
    """Pan portrait"""
    img = get_img(3000, 4000, "portrait")
    vid, _ = img.panorama(duration=3, speed=0.2, vspeed=0.1, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 3
    os.remove(vid)
    os.remove(img.filename)
