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
import subprocess
import platform
from unittest.mock import patch
from mediatools import encode
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.audiofile as audio

TMP_VID = util.get_tmp_file() + '.mp4'
TMP_AUDIO = util.get_tmp_file() + '.mp3'

def get_video():
    return 'it/video-1920x1080.mp4'


def test_encode_size():
    vid_o = video.VideoFile(get_video())
    video.HW_ACCEL = None
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution='1280x720', start=1, stop=2))
    assert vid2_o.resolution.width == 1280
    assert abs(vid2_o.duration - 1) < 0.1
    os.remove(TMP_VID)

def test_encode_bitrate():
    vid_o = video.VideoFile(get_video())
    video.HW_ACCEL = None
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution='640x360', vbitrate='1000k', abitrate='64k', start=1, stop=4))
    assert abs(vid2_o.video_bitrate - 1024 * 1024) < 200000
    assert abs(vid2_o.audio_bitrate - 64 * 1024) < 30000
    os.remove(TMP_VID)

def test_encode_acodec():
    vid_o = video.VideoFile(get_video())
    video.HW_ACCEL = None
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution='640x360', acodec='mp3', deinterlace=True, start=1, stop=2))
    assert vid2_o.audio_codec == 'mp3'
    os.remove(TMP_VID)

def test_encode_vcodec():
    vid_o = video.VideoFile(get_video())
    video.HW_ACCEL = None
    vid2_o = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution='640x360', vcodec='h265', deinterlace=True, start=1, stop=2))
    assert vid2_o.video_codec == 'hevc'
    os.remove(TMP_VID)

def test_hw_accel():
    video.HW_ACCEL = None
    assert video.use_hardware_accel(hw_accel=True, deinterlace=True)
    video.HW_ACCEL = None
    assert not video.use_hardware_accel(hw_accel=False, deinterlace=True)

def test_hw_accel_2():
    video.HW_ACCEL = True
    # HW accel expected to be available on Windows, not on Linux
    hw_accel_avail = (platform.system() == 'Windows')
    vid_o = video.VideoFile(get_video())
    try:
        _ = video.VideoFile(vid_o.encode(target_file=TMP_VID, resolution='640x360', abitrate='64k', start=1, stop=2))
        assert hw_accel_avail
    except subprocess.CalledProcessError:
        # Encoding will fail... just to cover some source code
        assert not hw_accel_avail

def test_main_file():
    video.HW_ACCEL = False
    file1 = 'it' + os.sep + 'video-720p.mp4'
    try:
        with patch.object(sys, 'argv', ['video-encode', '-g', '4', '-p', '1mbps', '-i', file1, '--resolution', '640x360']):
            encode.main()
        assert True
    except subprocess.CalledProcessError:
        # Encoding will fail... just to cover some source code
        assert False

def test_main_file_audio():
    video.HW_ACCEL = False
    util.set_debug_level(4)
    file1 = 'it' + os.sep + 'song.mp3'
    with patch.object(sys, 'argv', ['video-encode', '-p', 'mp3_128k', '-i', file1, '--outputfile', TMP_AUDIO]):
        encode.main()
    audio_f = audio.AudioFile(TMP_AUDIO)
    assert audio_f.acodec == 'mp3'
    assert audio_f.format == 'mp3'
    os.remove(TMP_AUDIO)


def test_main_dir_timeranges_1():
    video.HW_ACCEL = False
    file1 = 'it' + os.sep + 'video-720p.mp4'
    try:
        with patch.object(sys, 'argv', ['video-encode', '-p', '1mbps', '-i', file1, '--resolution', '640x360', '--timeranges', '00:02-00:04']):
            encode.main()
        # Can't delete output file, don't know the name
        assert True
    except subprocess.CalledProcessError:
        assert False

def test_main_dir_timeranges_2():
    video.HW_ACCEL = False
    file1 = 'it' + os.sep + 'video-720p.mp4'
    output = f"{file1}.out.mp4"
    try:
        with patch.object(sys, 'argv', ['video-encode', '-p', '1mbps', '-i', file1, '--resolution', '640x360',
                          '--timeranges', '00:00-00:01,00:02-00:04'], '-o', output):
            encode.main()
        # Output file is hardcoded for now :-(
        os.remove('it' + os.sep + 'video-720p.combined.mp4')
        assert True
    except subprocess.CalledProcessError:
        assert False