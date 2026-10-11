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

import datetime
import pytest
import os
import shutil
from unittest import mock
import mediatools.utilities as util
import mediatools.exceptions as ex
import mediatools.avfile as av
import mediatools.videofile as video

FILE = "it" + os.sep + "video-720p.mp4"
TMP1 = util.get_tmp_file() + ".mp4"
TMP2 = util.get_tmp_file() + ".mp4"


def test_type():
    try:
        _ = video.VideoFile("it" + os.sep + "seal.mp3")
        assert False
    except ex.FileTypeError:
        pass

    try:
        _ = video.VideoFile("it" + os.sep + "img-640x480.jpg")
        assert False
    except ex.FileTypeError:
        pass

    v = video.VideoFile(FILE)
    assert v.filename == FILE


def test_video_specs():
    v = video.VideoFile(FILE)
    v.probe()
    specs = v.get_video_specs()
    assert specs["streams"][0]["width"] == 1280
    assert specs["streams"][0]["codec_name"] == "h264"


def test_ffmpeg_cmdline():
    cmd1 = "-c:a libmp3lame -vn -b:a 192k -map_metadata 0 -id3v2_version 3 -write_id3v1 1"
    cmd2 = "-f mp4 -acodec aac -deinterlace -vcodec libx265 -f 60 -aspect 16:10 -b:v 1536k -s 720x400"
    assert video.get_size_option(cmd1) == ""
    assert video.get_size_option(cmd2) == "720x400"
    assert video.get_video_codec_option(cmd1) == ""
    assert video.get_video_codec_option(cmd2) == "libx265"
    assert video.get_audio_codec_option(cmd1) == "libmp3lame"
    assert video.get_audio_codec_option(cmd2) == "aac"
    assert video.get_format_option(cmd1) == ""
    assert video.get_format_option(cmd2) == "mp4"
    assert video.get_audio_bitrate_option(cmd1) == "192k"
    assert video.get_audio_bitrate_option(cmd2) == ""
    assert video.get_video_bitrate_option(cmd1) == ""
    assert video.get_video_bitrate_option(cmd2) == "1536k"
    assert video.get_aspect_ratio_option(cmd1) == ""
    assert video.get_aspect_ratio_option(cmd2) == "16:10"
    assert video.get_frame_rate_option(cmd1) == ""
    assert video.get_frame_rate_option(cmd2) == "60"


def test_video_props():
    f = video.VideoFile(FILE)
    h = f.get_video_properties()
    assert isinstance(h["file_size"], int)


def test_attributes():
    v = video.VideoFile(FILE)
    assert v.get_aspect_ratio() == "16:9"
    assert v.get_pixel_aspect_ratio() == "1:1"
    assert v.get_duration() == 10
    assert v.dimensions() == (1280, 720)
    assert v.get_width() == 1280
    assert v.get_height() == 720
    assert str(v.get_resolution()) == "1280x720"
    p = v.get_video_properties()
    assert p["file_size"] == 2001067
    p = v.get_properties()
    assert p["vbitrate"] == 1489365


def test_crop():
    v = video.VideoFile(FILE)
    # util.set_debug_level(4)
    cropv = video.VideoFile(v.crop(out_file=TMP1, width=160, height=160, position="center"))
    cropv.probe()
    assert cropv.aspect == "1:1"
    util.delete_files(cropv.filename)


def test_crop_box_position():
    v = video.VideoFile(FILE)
    cropv = video.VideoFile(v.crop(out_file=TMP1, box="160x120", position="top left"))
    cropv.probe()
    assert cropv.dimensions() == (160, 120)
    util.delete_files(cropv.filename)


def test_crop_too_big():
    v = video.VideoFile(FILE)
    w, h = v.dimensions()
    with pytest.raises(ValueError):
        v.crop(out_file=TMP1, box=f"{w + 2}x{h}")
    with pytest.raises(ValueError):
        v.crop(out_file=TMP1, box=f"{w}x{h + 2}")


def test_crop_command():
    """Crop keeps codec, copies other streams and sets a bitrate proportional to the cropped surface"""
    v = video.VideoFile(FILE)
    src_w, src_h = v.dimensions()
    w, h = src_w // 2, src_h // 2
    with mock.patch("mediatools.utilities.run_ffmpeg") as run:
        v.crop(out_file=TMP1, box=f"{w}x{h}", position="bottom right", hw_accel="off")
    cmd = run.call_args[0][0]
    assert "-map 0 -c copy" in cmd
    assert '-c:v "h264"' in cmd
    assert v.video_bitrate
    assert f"-b:v {int(v.video_bitrate * w * h / (src_w * src_h))}" in cmd
    assert f"crop={w}:{h}:{src_w - w}:{src_h - h}" in cmd
    assert "-hwaccel" not in cmd


def test_crop_default_output_name():
    """Without an output file the output is <name>.crop.<ext>"""
    v = video.VideoFile(FILE)
    with mock.patch("mediatools.utilities.run_ffmpeg"):
        out = v.crop(box="160x120", position="top left", hw_accel="off")
    assert out == v.filename.rsplit(".", 1)[0] + ".crop.mp4"


def test_crop_keeps_creation_date():
    """The cropped file gets the creation date of the source, set after encoding"""
    v = video.VideoFile(FILE)
    date = datetime.datetime(2020, 5, 17, 10, 30, 0)
    calls = []

    def fake_encode(*args, **kwargs):
        shutil.copy(FILE, TMP1)
        calls.append("encode")

    with (
        mock.patch("mediatools.videofile.get_creation_date", return_value=date) as get_date,
        mock.patch("mediatools.videofile.set_creation_date") as set_date,
        mock.patch("mediatools.utilities.run_ffmpeg", side_effect=fake_encode),
    ):
        set_date.side_effect = lambda *args, **kwargs: calls.append("set_date")
        v.crop(out_file=TMP1, box="160x120", hw_accel="off")
    get_date.assert_called_once_with(v.filename)
    set_date.assert_called_once_with(TMP1, date)
    assert calls == ["encode", "set_date"]
    util.delete_files(TMP1)


def test_crop_hw_accel_codec():
    """With HW acceleration the NVENC encoder matching the source codec is used"""
    v = video.VideoFile(FILE)
    v.get_specs()
    with mock.patch("mediatools.utilities.run_ffmpeg") as run:
        v.crop(out_file=TMP1, box="160x120", hw_accel="on")
    cmd = run.call_args[0][0]
    assert '-c:v "h264_nvenc"' in cmd
    assert "-hwaccel cuda" in cmd


def test_add_metadata():
    shutil.copy(FILE, TMP1)
    v = video.VideoFile(TMP1)
    outf = v.add_metadata(author="John Doe", year="2027", copyright="JDoe Corp", default_track=0, language=["0:fr:Croatian"])
    v2 = video.VideoFile(outf)
    v2.get_video_specs()
    # assert v2.author == 'John Doe'
    # assert int(v2.year) == 2027
    assert v2.copyright == "© JDoe Corp"
    os.remove(TMP1)
    os.remove(v2.filename)


def test_speed():
    v1 = video.VideoFile(FILE)
    v2 = video.VideoFile(video.speed(FILE, 2, output=TMP1))
    assert v1.duration == 2 * v2.duration
    os.remove(v2.filename)


def test_volume():
    v1 = video.VideoFile(FILE)
    v2 = video.VideoFile(video.volume(FILE, 2, output=TMP1))
    assert abs(v1.duration - v2.duration) < 0.1
    os.remove(v2.filename)


def test_reverse():
    v1 = video.VideoFile(FILE)
    v2 = video.VideoFile(video.reverse(FILE, output=TMP1))
    assert v1.duration == v2.duration
    os.remove(v2.filename)


def test_cut():
    start, stop = 0.5, 1.5
    v = video.VideoFile(av.cut(FILE, output=TMP1, start=start, stop=stop))
    assert abs(stop - start - v.duration) <= 0.06
    os.remove(v.filename)


def test_cut2():
    dur = 1.5
    v = video.VideoFile(av.cut(FILE, output=TMP1, stop=dur))
    assert abs(dur - v.duration) <= 0.06
    os.remove(v.filename)


def test_cut3():
    v = video.VideoFile(av.cut(FILE, output=TMP1, timeranges="00:00-00:02"))
    assert abs(2 - v.duration) <= 0.06
    os.remove(v.filename)


def test_specs2():
    v = video.VideoFile(FILE)
    assert v.get_video_codec(None) == "h264"
    assert v.get_audio_codec() == "aac"
    assert abs(v.get_video_duration() - 10.0) < 0.01
    assert abs(v.get_audio_bitrate() - 96966) < 10


def test_metadata():
    v = video.VideoFile(FILE)
    a = "John"
    v.set_author(a)
    assert v.author == a
    assert v.get_author() == a
    c = "(c) John"
    v.set_copyright(c)
    assert v.copyright == c
    assert v.get_copyright() == c
    out = video.VideoFile(v.add_author("Olivier"))
    assert abs(v.duration - out.duration) < 0.02
    out = video.VideoFile(v.add_year("2021"))
    assert abs(v.duration - out.duration) < 0.02
    assert v.get_audio_codec() == "aac"
    assert (v.get_video_duration() - 10.0) < 0.01
    assert (v.get_audio_bitrate() - 96966) < 10
