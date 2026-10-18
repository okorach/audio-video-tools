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

"""Tests of the copy of the creation date and geotagging from the source to the generated files"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import shutil
import subprocess
from unittest import mock

import pytest
from exiftool import ExifToolHelper

import mediatools.utilities as util
from mediatools import metacopy
from mediatools import videofile as video

DATE = "2018:03:02 08:09:10"

pytestmark = pytest.mark.skipif(shutil.which(util.get_exiftool()) is None, reason="exiftool is not installed")


def ffmpeg(*args: str) -> None:
    subprocess.run([util.get_ffmpeg(), "-v", "error", "-y", *args], check=True)


@pytest.fixture(scope="module")
def geotagged_video(tmp_path_factory) -> str:
    """A video with an audio track, created on 2018-03-02 at 08:09:10 UTC and located at 10.5 N, 20.25 W"""
    path = tmp_path_factory.mktemp("geo") / "geo.mp4"
    ffmpeg(
        *("-f", "lavfi", "-i", "testsrc=size=160x90:rate=10:duration=1", "-f", "lavfi", "-i", "sine=duration=1"),
        *("-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest"),
        *("-metadata", "creation_time=2018-03-02T08:09:10Z", "-metadata", "location=+10.5-020.25/", str(path)),
    )
    return str(path)


def exif(path: str) -> dict:
    with ExifToolHelper(executable=util.get_exiftool()) as et:
        return et.get_metadata(path, params=["-n"])[0]


def assert_same_date_and_place(path: str) -> None:
    data = exif(path)
    assert data["File:FileModifyDate"].startswith(DATE)
    assert float(data["Composite:GPSLatitude"]) == pytest.approx(10.5, abs=1e-3)
    assert float(data["Composite:GPSLongitude"]) == pytest.approx(-20.25, abs=1e-3)


def test_find_source_and_target(geotagged_video, tmp_path):
    target = tmp_path / "out.mp4"
    target.write_bytes(b"x")
    assert metacopy.find_source_and_target(f'-i "{geotagged_video}" -vf scale=80:-2 "{target}"') == (geotagged_video, str(target))
    assert metacopy.find_source_and_target(f'-ss 1 -i "{geotagged_video}" -frames:v 1 {target}') == (geotagged_video, str(target))


def test_find_source_and_target_ignores_commands_without_media_output(geotagged_video, tmp_path):
    target = tmp_path / "result.trf"
    target.write_bytes(b"x")
    assert metacopy.find_source_and_target(f'-i "{geotagged_video}" -f null -') == (None, None)
    assert metacopy.find_source_and_target(f'-i "{geotagged_video}" "{target}"') == (None, None)
    assert metacopy.find_source_and_target('-i "missing.mp4" "missing-out.mp4"') == (None, None)


def test_find_source_skips_inputs_that_are_not_media_files(geotagged_video, tmp_path):
    target = tmp_path / "out.mp4"
    target.write_bytes(b"x")
    assert metacopy.find_source_and_target(f'-f lavfi -i color=c=black -i "{geotagged_video}" "{target}"')[0] == geotagged_video


@pytest.mark.parametrize(("extra", "extension"), [(["-vf", "scale=80:-2"], "mp4"), (["-frames:v", "1", "-update", "1"], "jpg"), (["-vn"], "m4a")])
def test_run_ffmpeg_copies_date_and_geotag(geotagged_video, tmp_path, extra, extension):
    target = str(tmp_path / f"out.{extension}")
    util.run_ffmpeg(f'-i "{geotagged_video}" {" ".join(extra)} "{target}"')
    assert_same_date_and_place(target)


def test_run_ffmpeg_copies_the_date_to_formats_without_geotagging(geotagged_video, tmp_path):
    target = str(tmp_path / "out.mp3")
    util.run_ffmpeg(f'-i "{geotagged_video}" -vn "{target}"')
    assert exif(target)["File:FileModifyDate"].startswith(DATE)


def test_run_ffmpeg_without_gps_copies_only_the_date(short_video, tmp_path):
    source = str(tmp_path / "nogps.mp4")
    ffmpeg("-i", short_video, "-c", "copy", "-metadata", "creation_time=2018-03-02T08:09:10Z", source)
    target = str(tmp_path / "out.mp4")
    util.run_ffmpeg(f'-i "{source}" -vf scale=80:-2 "{target}"')
    data = exif(target)
    assert data["File:FileModifyDate"].startswith(DATE)
    assert "Composite:GPSLatitude" not in data


def test_copy_never_fails(geotagged_video, tmp_path):
    with mock.patch.object(metacopy, "ExifToolHelper", side_effect=FileNotFoundError):
        metacopy.copy_date_and_geotag(geotagged_video, str(tmp_path / "x.mp4"))
    with mock.patch.object(metacopy, "ExifToolHelper", side_effect=RuntimeError("boom")):
        metacopy.copy_date_and_geotag(geotagged_video, str(tmp_path / "x.mp4"))


def test_copy_after_ffmpeg_does_nothing_without_target(tmp_path):
    with mock.patch.object(metacopy, "copy_date_and_geotag") as copy:
        metacopy.copy_after_ffmpeg("-i nothing -f null -")
    copy.assert_not_called()


def test_tools_keep_the_date_and_geotag(geotagged_video, tmp_path):
    out = video.speed(geotagged_video, "2", output=str(tmp_path / "fast.mp4"))
    assert_same_date_and_place(out)
    out = video.VideoFile(geotagged_video).encode(target_file=str(tmp_path / "enc.mp4"), vcodec="h265", width=80, hw_accel="off")
    assert_same_date_and_place(out)
