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
import mediatools.resolution as res

FILE = "it" + os.sep + "video-720p.mp4"
FILE_SIZE = 2001067
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
    assert v.filename == os.path.abspath(FILE)


def test_video_specs():
    v = video.VideoFile(FILE)
    v.probe()
    specs = v.get_video_specs()
    assert specs["streams"][0]["width"] == 1280
    assert specs["streams"][0]["codec_name"] == "h264"


def test_ffmpeg_cmdline():
    cmd1 = "-c:a libmp3lame -vn -b:a 192k -map_metadata 0 -id3v2_version 3 -write_id3v1 1"
    cmd2 = "-f mp4 -acodec aac -deinterlace -vcodec libx265 -r 60 -aspect 16:10 -b:v 1536k -s 720x400"
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


def test_crop(short_video):
    v = video.VideoFile(short_video)
    # util.set_debug_level(4)
    cropv = video.VideoFile(v.crop(out_file=TMP1, width=160, height=160, position="center"))
    cropv.probe()
    assert cropv.aspect == "1:1"
    util.delete_files(cropv.filename)


def test_crop_box_position(short_video):
    v = video.VideoFile(short_video)
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
    assert "-map 0:v? -map 0:a? -map 0:s? -c copy" in cmd
    assert '-c:v:0 "h264"' in cmd
    assert v.video_bitrate
    assert f"-b:v:0 {int(v.video_bitrate * w * h / (src_w * src_h))}" in cmd
    assert f"crop={w}:{h}:{src_w - w}:{src_h - h}" in cmd
    assert "-hwaccel" not in cmd


def _rotated_video(rotation: int, streams: list | None = None) -> video.VideoFile:
    """A video whose first video stream is 1280x720 with the given rotation"""
    v = video.VideoFile(FILE)
    v.probe()
    main = {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720, "side_data_list": [{"rotation": rotation}]}
    v.specs = {"streams": streams or [main]}
    v.resolution = res.Resolution(width=1280, height=720)
    v.get_specs = mock.Mock()
    v.video_codec = "h264"
    v.video_bitrate = 1_000_000
    return v


@pytest.mark.parametrize(("rotation", "expected"), [(0, (1280, 720)), (90, (720, 1280)), (-90, (720, 1280)), (180, (1280, 720)), (270, (720, 1280))])
def test_displayed_dimensions(rotation, expected):
    """The displayed dimensions take the rotation of the video into account"""
    assert _rotated_video(rotation).displayed_dimensions() == expected


def test_crop_rotated_video_too_big():
    """A crop is validated against the displayed size: 720 wide for a 1280x720 video rotated by 90 degrees"""
    v = _rotated_video(90)
    with pytest.raises(ValueError, match="bigger than source video 720x1280"):
        v.crop(out_file=TMP1, box="1280x720", hw_accel="off")


def test_crop_rotated_video_position():
    """The crop position is computed on the displayed frame"""
    v = _rotated_video(90)
    with mock.patch("mediatools.utilities.run_ffmpeg") as run, mock.patch("mediatools.videofile.get_creation_date", return_value=None):
        v.crop(out_file=TMP1, box="720x720", position="bottom", hw_accel="off")
    assert "crop=720:720:0:560" in run.call_args[0][0]


def test_crop_only_filters_main_video_stream():
    """With a thumbnail video stream after the main video, only the main video is filtered and re-encoded"""
    streams = [
        {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720},
        {"codec_type": "audio", "codec_name": "aac"},
        {"codec_type": "video", "codec_name": "mjpeg", "width": 960, "height": 720},
    ]
    v = _rotated_video(0, streams)
    assert v.__main_video_stream_position__() == 0
    with mock.patch("mediatools.utilities.run_ffmpeg") as run, mock.patch("mediatools.videofile.get_creation_date", return_value=None):
        v.crop(out_file=TMP1, box="640x360", hw_accel="off")
    cmd = run.call_args[0][0]
    assert "-filter:v:0 " in cmd
    assert "-c copy -c:v:0" in cmd
    assert "-b:v:0 " in cmd


def test_main_video_stream_position():
    """The position is the rank of the main video stream among the video streams"""
    streams = [
        {"codec_type": "audio", "codec_name": "aac"},
        {"codec_type": "video", "codec_name": "gif"},
        {"codec_type": "video", "codec_name": "h264"},
    ]
    assert _rotated_video(0, streams).__main_video_stream_position__() == 1


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
    assert '-c:v:0 "h264_nvenc"' in cmd
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
    # Twice as fast: half the duration, to the precision of 2 frames
    assert abs(v1.duration / 2 - v2.duration) < 0.1
    os.remove(v2.filename)


def test_volume(short_video):
    v1 = video.VideoFile(short_video)
    v2 = video.VideoFile(video.volume(short_video, 2, output=TMP1))
    assert abs(v1.duration - v2.duration) < 0.1
    os.remove(v2.filename)


def test_reverse(short_video):
    v1 = video.VideoFile(short_video)
    v2 = video.VideoFile(video.reverse(short_video, output=TMP1))
    assert abs(v1.duration - v2.duration) < 0.1
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


@pytest.mark.parametrize(
    ("hw_accel", "options", "expected"),
    [
        (True, {"width": 640}, '-vf "scale_cuda=640:-2"'),
        (True, {"height": 360}, '-vf "scale_cuda=-2:360"'),
        (True, {"width": 640, "height": 360}, '-vf "scale_cuda=640:360"'),
        (True, {"resolution": "640x360"}, '-vf "scale_cuda=640:360"'),
        (False, {"width": 640}, '-vf "scale=640:-2"'),
        (False, {"height": 360}, '-vf "scale=-2:360"'),
        (False, {"width": 640, "height": 360}, '-vf "scale=640:360"'),
        (False, {"resolution": "640x360"}, '-s "640x360"'),
    ],
)
def test_encode_resize_options(hw_accel, options, expected):
    """--width, --height and --resolution are all honored, with or without HW acceleration"""
    v = video.VideoFile(FILE)
    with mock.patch("mediatools.utilities.run_ffmpeg") as run:
        v.encode(target_file=TMP1, hw_accel=hw_accel, vcodec="x265", **options)
    assert expected in run.call_args[0][0]


@pytest.mark.parametrize("hw_accel", [True, False])
def test_encode_no_resize(hw_accel):
    """Without --width, --height or --resolution the video is not scaled"""
    v = video.VideoFile(FILE)
    with mock.patch("mediatools.utilities.run_ffmpeg") as run:
        v.encode(target_file=TMP1, hw_accel=hw_accel, vcodec="x265")
    cmd = run.call_args[0][0]
    assert "scale" not in cmd
    assert " -s " not in cmd


def test_properties_do_not_alter_the_object():
    """Reading the properties of a file doesn't change the attributes of the object (the size is still a method)"""
    v = video.VideoFile(FILE)
    props = v.get_properties()
    assert props["file_size"] == FILE_SIZE
    assert props["size"] == FILE_SIZE
    assert v.size() == FILE_SIZE
    assert v.get_properties()["file_size"] == FILE_SIZE


@pytest.mark.parametrize("hw_accel", [True, False])
def test_deinterlace_uses_yadif(hw_accel):
    """-deinterlace is not supported by recent ffmpeg versions: the yadif filter is used instead"""
    v = video.VideoFile(FILE)
    with mock.patch("mediatools.utilities.run_ffmpeg") as run:
        v.encode(target_file=TMP1, hw_accel=hw_accel, deinterlace=True, vcodec="x264")
    cmd = run.call_args[0][0]
    assert '-vf "yadif"' in cmd
    assert "-deinterlace" not in cmd


def test_profile_deinterlace_uses_yadif():
    """A profile with the -deinterlace option also uses the yadif filter"""
    v = video.VideoFile(FILE)
    with (
        mock.patch("mediatools.utilities.run_ffmpeg") as run,
        mock.patch("mediatools.utilities.get_profile_params", return_value={"f": "mp4", "deinterlace": True}),
    ):
        v.encode(target_file=TMP1, profile="any", hw_accel=False)
    cmd = run.call_args[0][0]
    assert '-vf "yadif"' in cmd
    assert "-deinterlace" not in cmd


def test_no_deinterlace_by_default():
    v = video.VideoFile(FILE)
    with mock.patch("mediatools.utilities.run_ffmpeg") as run:
        v.encode(target_file=TMP1, hw_accel=False, vcodec="x264")
    assert "yadif" not in run.call_args[0][0]
