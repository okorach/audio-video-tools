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
import sys
from unittest.mock import patch
import pytest
import mediatools.videofile as video
import mediatools.imagefile as image
import mediatools.media_config as conf
from mediatools import slideshow

large_img = None
portrait_img = None

images_full = (
    "it" + os.sep + "img-1770x1291.jpg",
    "it" + os.sep + "img-3000x1682.jpg",
    "it" + os.sep + "img-large.jpg",
    "it" + os.sep + "img-2320x4000.jpg",
    "it" + os.sep + "img-superwide.jpg",
    "it" + os.sep + "img-2880x1924.jpg",
    "it" + os.sep + "img-3000x4000.jpg",
    "it" + os.sep + "img-640x480.jpg",
)

# The slideshow converts each image to a video: the tests use small versions of landscape and portrait images
SMALL_IMAGES = (("img-1770x1291.jpg", 400), ("img-3000x4000.jpg", 300), ("img-640x480.jpg", 320))


@pytest.fixture(scope="module")
def images(tmp_path_factory):
    folder = tmp_path_factory.mktemp("slides")
    return tuple(image.ImageFile("it" + os.sep + name).scale(width, -1, out_file=str(folder / name)) for name, width in SMALL_IMAGES)


@pytest.fixture
def small_default_resolution(monkeypatch):
    """Generate the videos of the slideshows in 320x180 instead of the default resolution"""
    real_get_property = conf.get_property
    monkeypatch.setattr(
        conf, "get_property", lambda name, settings=None: "320x180" if name == conf.VIDEO_RESOLUTION_KEY else real_get_property(name, settings)
    )


def test_slideshow(images):
    # util.set_debug_level(4)
    vid2_o = video.VideoFile(video.slideshow(*images, resolution="360x200")[0])
    assert vid2_o.duration > 12
    assert vid2_o.resolution.width == 360
    assert vid2_o.resolution.height == 200
    os.remove(vid2_o.filename)


def test_slideshow_without_resolution(images, small_default_resolution):
    # util.set_debug_level(4)
    vid2_o = video.VideoFile(video.slideshow(*images)[0])
    assert vid2_o.duration > 12
    os.remove(vid2_o.filename)


def test_main(images):
    file1, file2 = images[2], images[0]
    with patch.object(sys, "argv", ["video-slideshow", "-g", "4", file1, "--resolution", "640x360", file2]):
        slideshow.main()
