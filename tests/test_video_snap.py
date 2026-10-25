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

"""Tests of video-snap, with the ffmpeg commands mocked"""

import os
import shutil
import sys
from pathlib import Path
from unittest import mock

import pytest

from mediatools import tools
from mediatools import video_snap as vs


def test_snap_times_nbr_photos() -> None:
    assert vs.snap_times(100.0, nbr_photos=4) == pytest.approx([20.0, 40.0, 60.0, 80.0])
    assert vs.snap_times(10.0, nbr_photos=1) == pytest.approx([5.0])


def test_snap_times_every() -> None:
    assert vs.snap_times(25.0, every=10) == [10, 20]
    assert vs.snap_times(20.0, every=10) == [10]  # No photo at the very end
    assert vs.snap_times(5.0, every=10) == []


def test_photo_name_padding() -> None:
    assert vs.photo_name("dir/foo.mp4", 1, 9).endswith("foo.1.jpg")
    assert vs.photo_name("dir/foo.mp4", 1, 10).endswith("foo.01.jpg")
    assert vs.photo_name("dir/foo.mp4", 7, 100).endswith("foo.007.jpg")
    assert vs.photo_name("dir/foo.mp4", 3, 5, "out").replace("\\", "/") == "out/foo.3.jpg"


def test_snap_file(monkeypatch: pytest.MonkeyPatch) -> None:
    run = mock.Mock()
    monkeypatch.setattr(vs.video, "get_duration", lambda _f: 30.0)
    monkeypatch.setattr(vs.util, "run_ffmpeg", run)
    monkeypatch.setattr(vs.util, "generated_file", mock.Mock())
    photos = vs.snap_file("dir/foo.mp4", nbr_photos=2)
    assert [p.replace("\\", "/") for p in photos] == ["dir/foo.1.jpg", "dir/foo.2.jpg"]
    assert run.call_count == 2
    assert run.call_args_list[0].args[0].startswith("-ss 10.000 -i ")


def test_snap_file_without_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vs.video, "get_duration", lambda _f: None)
    with pytest.raises(ValueError, match="duration"):
        vs.snap_file("foo.mp4", every=5)


def run_main(monkeypatch: pytest.MonkeyPatch, *args: object) -> None:
    monkeypatch.setattr(vs.util, "expand_input_files", lambda inputs, *_a, **_k: inputs)
    with mock.patch.object(sys, "argv", ["videotool", "snap", *args]):
        tools.videotool()


def test_main_every(monkeypatch: pytest.MonkeyPatch) -> None:
    snap = mock.Mock()
    monkeypatch.setattr(vs, "snap_file", snap)
    run_main(monkeypatch, "-i", "a.mp4", "b.mp4", "--every", "2.5")
    assert [c.args for c in snap.call_args_list] == [("a.mp4", None, 2.5, None), ("b.mp4", None, 2.5, None)]


def test_main_requires_one_option(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit):
        run_main(monkeypatch, "-i", "a.mp4")
    with pytest.raises(SystemExit):
        run_main(monkeypatch, "-i", "a.mp4", "--every", "2", "--nbr_photos", "3")


def test_main_rejects_non_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit) as e:
        run_main(monkeypatch, "-i", "a.mp4", "--nbr_photos", "0")
    assert e.value.code == 2


def test_snap_real_video_nbr_photos(video_5s: str) -> None:
    photos = vs.snap_file(video_5s, nbr_photos=4)
    assert [os.path.basename(p) for p in photos] == [f"video-5s.{i}.jpg" for i in range(1, 5)]
    assert all(Path(p).stat().st_size > 0 for p in photos)


def test_snap_real_video_every_in_output_dir(video_5s: str, tmp_path: Path) -> None:
    photos = vs.snap_file(video_5s, every=1, out_dir=str(tmp_path / "photos"))
    assert sorted(os.listdir(tmp_path / "photos")) == [f"video-5s.{i}.jpg" for i in range(1, 5)]
    assert len(photos) == 4


def test_snap_real_video_zero_padding(video_5s: str, tmp_path: Path) -> None:
    photos = vs.snap_file(video_5s, every=0.5, out_dir=str(tmp_path))
    assert len(photos) == 9
    assert os.path.basename(photos[0]) == "video-5s.1.jpg"
    photos = vs.snap_file(video_5s, every=0.25, out_dir=str(tmp_path))
    assert len(photos) == 19
    assert os.path.basename(photos[0]) == "video-5s.01.jpg"


def test_main_real_directory(video_5s: str, tmp_path: Path) -> None:
    shutil.copy(video_5s, tmp_path / "a.mp4")
    with mock.patch.object(sys, "argv", ["videotool", "snap", "-i", str(tmp_path), "--nbr_photos", "2"]):
        tools.videotool()
    assert sorted(f for f in os.listdir(tmp_path) if f.endswith(".jpg")) == ["a.1.jpg", "a.2.jpg"]
