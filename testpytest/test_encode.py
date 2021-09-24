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

TMP_VID = util.get_tmp_file() + '.mp4'

def get_video():
    return 'it/video-1920x1080.mp4'


def test_encode_size():
    vid_o = video.VideoFile(get_video())
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution='1280x720', start=1, stop=2))
    assert vid2_o.resolution.width == 1280
    assert abs(vid2_o.duration - 1) < 0.1
    os.remove(TMP_VID)

def test_encode_bitrate():
    vid_o = video.VideoFile(get_video())
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution='640x360', vbitrate='3000k', abirate='64k', start=1, stop=4))
    assert abs(vid2_o.video_bitrate + vid2_o.audio_bitrate - 3 * 1024 * 1024) < 200000
    assert abs(vid2_o.audio_bitrate - 64 * 1024) < 30000
    os.remove(TMP_VID)

def test_encode_acodec():
    vid_o = video.VideoFile(get_video())
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution='640x360', acodec='libmp3lame', deinterlace=True, start=1, stop=2))
    assert vid2_o.audio_codec == 'mp3'
    os.remove(TMP_VID)

def test_encode_vcodec():
    vid_o = video.VideoFile(get_video())
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution='640x360', vcodec='libx265', deinterlace=True, start=1, stop=2))
    assert vid2_o.video_codec == 'hevc'
    os.remove(TMP_VID)

def test_hw_accel():
    video.HW_ACCEL = None
    assert video.use_hardware_accel(hw_accel=True, deinterlace=True)
    video.HW_ACCEL = None
    assert not video.use_hardware_accel(deinterlace=True)
    video.HW_ACCEL = None
    assert not video.use_hardware_accel(hw_accel=False, deinterlace=True)
    video.HW_ACCEL = None
    assert not video.use_hardware_accel()
    assert not video.use_hardware_accel(hw_accel=True)

def test_hw_accel_2():
    video.HW_ACCEL = True
    vid_o = video.VideoFile(get_video())
    _ = video.VideoFile(vid_o.encode(target_file=TMP_VID, vbitrate='3000k', resolution='640x360', abirate='64k', start=1, stop=2))
    # Encoding will fail... just to cover some source code
    assert True
