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
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.exceptions as ex

large_img = None
portrait_img = None

images = (
    "it/img-1770x1291.jpg", "it/img-3000x1682.jpg", "it/img-large.jpg",
    "it/img-2320x4000.jpg", "it/img-superwide.jpg", "it/img-2880x1924.jpg",
    "it/img-3000x4000.jpg", "it/img-640x480.jpg"
)

def test_slideshow():
    util.set_debug_level(5)
    vid2_o = video.VideoFile(video.slideshow(*images, resolution="360x200"))
    assert vid2_o.duration > 20
    os.remove('slideshow.mp4')

def test_slideshow_without_resolution():
    util.set_debug_level(5)
    vid2_o = video.VideoFile(video.slideshow(*images))
    assert vid2_o.duration > 20
    os.remove('slideshow.mp4')
