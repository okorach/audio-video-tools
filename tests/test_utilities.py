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
import platform
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.options as opt

CMD = 'test_utilities'
VIDEO = 'it' + os.sep + 'video-720p.mp4'
TMP1 = util.get_tmp_file() + '.mp4'

def test_conf():
    assert util.get_conf_property('default.image.format') == 'jpg'

def test_hms():
    assert util.to_hms('3727.21') == (1, 2, 7.21)
    assert util.to_hms('7227.33', fmt='string') == "02:00:27.330"
    assert util.to_hms('notfloat') == (0, 0, 0)
    assert util.to_hms('notfloat', fmt='string') == "00:00:00"

def test_to_seconds():
    assert util.to_seconds("02:00:07.327") == 7207.327
    assert util.to_seconds("02:19.111") == 139.111
    assert util.to_seconds("319.111") == 319.111

def test_profile():
    assert util.get_profile_extension(None) == 'mp4'
    assert util.get_profile_extension('mp3_128k') == 'mp3'
    assert util.get_profile_extension('nonexisting') == 'mp4'

def test_generated():
    util.generated_file("foo.txt")
    assert True

def test_args():
    parser = util.get_common_args("Tester", "media-tools unit testing")
    parser = video.add_video_args(parser)
    kw = util.parse_media_args(parser, ['-i', 'file.mp4', '--resolution', '640x480'])
    assert kw['width'] == 640
    assert kw['resolution'] == '640x480'
    assert kw['inputfile'] == 'file.mp4'
    assert 'aspect' not in kw

    kw = util.parse_media_args(parser, ['-i', 'file2.mp4', '--resolution', 'x480'])
    assert kw['width'] == -1

    kw = util.parse_media_args(parser, ['-i', 'file3.mp4', '--resolution', '1280x'])
    assert kw['width'] == 1280
    assert kw['height'] == -1

    kw = util.parse_media_args(parser, ['-i', 'file4.mp4', '--resolution', '1280x720', '-t', '07:00-12:00'])
    assert kw['start'] == '07:00'
    assert kw['stop'] == '12:00'

def test_ffmpeg_cmdline():
    assert util.get_ffmpeg_cmdline_params("-i  file.mp4 -ss 0 -f  mp4 -s   620x300 -r 50 -aspect 16:9")[opt.Option.RESOLUTION] == '620x300'

def test_pct():
    assert util.percent_or_absolute("17%") == 0.17
    assert util.percent_or_absolute("0.113") == 0.113
    assert util.percent_or_absolute("12%", 2) == 0.24

def test_find_key():
    data = {"one": 1, "two": 2, "three": 3}
    assert util.find_key(data, ("two", "three")) == 2
    assert util.find_key(data, ("four", "three")) == 3
    assert util.find_key(data, ("four", "five")) is None

def test_dict2str():
    assert util.dict2str({"verbose": True, "bitrate": 20}) == " -verbose -bitrate 20"
    assert util.dict2str({"verbose": False, "bitrate": 20}) == " -bitrate 20"
    assert util.dict2str({}) == ""

def test_swap_kv():
    assert util.swap_keys_values({"one": 1, "two": 2, "three": 3}) == {1: "one", 2: "two", 3: "three"}

def test_ffmpeg_cmd_line():
    cmd = " -f mp4 -acodec aac -ac 2 -b:a 128k -vcodec libx264 -an -b:v 3072k -r 25 -aspect 4:3  -s 1280x720"
    d = util.get_ffmpeg_cmdline_params(cmd)
    assert d[opt.Option.FORMAT] == "mp4"
    assert d[opt.Option.ACODEC] == "aac"
    assert d[opt.Option.ACHANNEL] == "2"
    assert d[opt.Option.ABITRATE] == "128k"
    assert d[opt.Option.VCODEC] == "libx264"
    assert d[opt.Option.MUTE]
    assert not d[opt.Option.VMUTE]
    assert d[opt.Option.VBITRATE] == "3072k"
    assert d[opt.Option.FPS] == "25"
    assert d[opt.Option.RESOLUTION] == "1280x720"
    assert d[opt.Option.ASPECT] == "4:3"
    assert not d[opt.Option.DEINTERLACE]

def test_ffmpeg_cmd_line_2():
    cmd = " -c:v libx266 -deinterlace  -c:a aac2"
    d = util.get_ffmpeg_cmdline_params(cmd)
    assert opt.Option.FORMAT not in d
    assert d[opt.Option.ACODEC] == "aac2"
    assert opt.Option.ABITRATE not in d
    assert d[opt.Option.VCODEC] == "libx266"
    assert opt.Option.VBITRATE not in d
    assert opt.Option.FPS not in d
    assert opt.Option.RESOLUTION not in d
    assert opt.Option.ASPECT not in d
    assert d[opt.Option.DEINTERLACE]

def test_ffmpeg_cmd_line_3():
    cmd = " -codec:a aac3 -codec:v libx267 -deinterlace "
    d = util.get_ffmpeg_cmdline_params(cmd)
    assert d[opt.Option.ACODEC] == "aac3"
    assert d[opt.Option.VCODEC] == "libx267"

def test_cmd_line_params():
    cmd = " -thebest olivier -b:a   128k  -deinterlace   -an -acodec aac "
    d = util.get_cmdline_params(cmd)
    assert d == {'thebest': 'olivier', 'b:a': '128k', 'acodec': 'aac', 'deinterlace': True, 'an': True}

def test_to_hms_str():
    assert util.to_hms_str(152.2) == "00:02:32.200"
    assert util.to_hms_str("3662.23") == "01:01:02.230"

def test_to_seconds2():
    assert util.to_seconds("00:02:32.200") == 152.2
    assert util.to_seconds("1:01:02.230") == 3662.23
    assert util.to_seconds("05:03.210") == 303.21
    assert util.to_seconds("03.210") == 3.21

def test_difftime():
    assert abs(util.difftime("02:57:21.931", "01:34:10.311") - (3600 + 23 * 60 + 11.620)) < 0.0000001

def test_ar():
    cmd = "-f mp4 -acodec aac -ac 2 -b:a 128k -vcodec libx264 -an -b:v 3072k -r 25 -aspect 4:3  -s 1280x720"
    assert util.get_ffmpeg_cmdline_param(cmd, opt.OptionFfmpeg.SAMPLERATE) is None
    cmd = "-f mp4 -acodec aac -ac 2 -b:a 128k   -ar  44k -vcodec libx264 -an -b:v 3072k -r 25  -s 1280x720"
    assert util.get_ffmpeg_cmdline_param(cmd, opt.OptionFfmpeg.SAMPLERATE) == "44k"

def test_eta():
    assert util.__compute_eta__("what the heck", 10) == ''
    assert util.__compute_eta__("frame=30608 fps=197 q=25.0 size=  330kB"
                                " time=00:00:10.00 bitrate=2261.3kbits/s speed=10x", 20) == " ETA=00:00:01.000"
    assert util.__compute_eta__("frame=30608 fps=197 q=25.0 size=  3920kB"
                                " time=00:00:10.000 bitrate=2261.3kbits/s speed=5x", 20) == " ETA=00:00:02.000"
    assert util.__compute_eta__("frame=30608 fps=197 q=25.0 size=3320kB"
                                " time=00:00:10.000 bitrate=2261.3kbits/s speed=0x", 20) == " ETA=Undefined"
    assert util.__compute_eta__("frame=30608 fps=197 q=25.0 size=  7920kB"
                                " tim=00:00:10.000 bitrate=2261.3kbits/s speed=10x", 20) == ""
    assert util.__compute_eta__("frame=30608 fps=197 q=25.0 size=  7920kB"
                                " time=00:00:10.000 bitrate=2261.3kbits/s sped=10x", 20) == ""

def test_hw_accel_auto():
    util.set_debug_level(4)
    util.HW_ACCEL = None
    assert not util.use_hardware_accel(hw_accel='auto', deinterlace=True)

def test_hw_accel_off():
    util.HW_ACCEL = None
    assert not util.use_hardware_accel(hw_accel='off')

def test_hw_accel_on():
    util.HW_ACCEL = None
    assert util.use_hardware_accel(hw_accel='on', deinterlace=True)

def test_hw_accel_without_gpu():
    util.HW_ACCEL = None
    auto_accel = util.use_hardware_accel(hw_accel='auto')
    if platform.system() == 'Windows':
        assert auto_accel
    else:
        assert not auto_accel
