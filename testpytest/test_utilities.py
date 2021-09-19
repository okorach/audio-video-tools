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

import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.options as opt

def test_conf():
    assert util.get_conf_property('image.default.format') == 'jpg'

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
    kw = util.parse_media_args(parser, ['-i', 'file.mp4', '-s', '640x480'])
    assert kw['width'] == 640
    assert kw['resolution'] == '640x480'
    assert kw['inputfile'] == 'file.mp4'
    assert 'aspect' not in kw

    kw = util.parse_media_args(parser, ['-i', 'file2.mp4', '-s', 'x480'])
    assert kw['width'] == -1

    kw = util.parse_media_args(parser, ['-i', 'file3.mp4', '-s', '1280x'])
    assert kw['width'] == 1280
    assert kw['height'] == -1

    kw = util.parse_media_args(parser, ['-i', 'file4.mp4', '-s', '1280x720', '-t', '07:00-12:00'])
    assert kw['start'] == '07:00'
    assert kw['stop'] == '12:00'

def test_ffmpeg_cmdline():
    assert util.get_ffmpeg_cmdline_framesize("-i  file.mp4 -ss 0 -f  mp4 -s   620x300 -r 50 -aspect 16:9") == '620x300'

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
    cmd = "-f mp4 -acodec aac -ac 2 -b:a 128k -vcodec libx264 -an -b:v 3072k -r 25 -aspect 4:3  -s 1280x720"
    d = util.get_ffmpeg_cmdline_params(cmd)
    assert d[opt.Option.FORMAT] == "mp4"
    assert d[opt.Option.ACODEC] == "aac"
    assert d[opt.Option.ACHANNEL] == "2"
    assert d[opt.Option.ABITRATE] == "128k"
    assert d[opt.Option.VCODEC] == "libx264"
    assert d["amute"]
    assert not d["vmute"]
    assert d[opt.Option.VBITRATE] == "3072k"
    assert d[opt.Option.FPS] == "25"
    assert d[opt.Option.RESOLUTION] == "1280x720"
    assert d[opt.Option.ASPECT] == "4:3"
    assert not d[opt.Option.DEINTERLACE]

def test_to_hms_str():
    assert util.to_hms_str(152.2) == "00:02:32.200"
    assert util.to_hms_str("3662.23") == "01:01:02.230"

def test_to_seconds2():
    assert util.to_seconds("00:02:32.200") == 152.2
    assert util.to_seconds("01:01:02.230") == 3662.23
    assert util.to_seconds("05:03.210") == 303.21
    assert util.to_seconds("03.210") == 3.21

def test_difftime():
    assert util.difftime("02:57:21.931", "01:34:10.311") == "01:23:11:620"
