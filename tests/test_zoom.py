
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
import mediatools.imagefile as image
import mediatools.videofile as video

TMP_VID = util.get_tmp_file() + '.mp4'
TMP_IMG = util.get_tmp_file() + '.jpg'

def get_img(w, h, orientation='landscape'):
    small_img = image.get_background('black')
    portrait_img = image.ImageFile(image.ImageFile(small_img).scale(w, h, out_file=TMP_IMG))
    portrait_img.orientation = orientation
    return portrait_img


def test_zoom_landscape():
    img = get_img(4000, 3000)
    (vid, _) = img.zoom(duration=3, speed=0.2, vspeed=0.1, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 3
    os.remove(vid)
    os.remove(img.filename)

def test_zoom_portrait():
    img = get_img(2000, 3000, 'portrait')
    (vid, _) = img.zoom(duration=3, speed=0.2, vspeed=0.1, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 3
    os.remove(vid)
    os.remove(img.filename)

def test_zoom_glob_1():
    (vid, _) = image.zoom(image.get_background('black'), zoom_level=1.3, duration=3, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 3
    os.remove(vid)

def test_zoom_glob_2():
    (vid, _) = image.zoom(image.get_background('black'), zoom_level=-1.2, duration=5, resolution="720x400", out_file=TMP_VID)
    vid_o = video.VideoFile(vid)
    assert vid_o.duration == 5
    os.remove(vid)
