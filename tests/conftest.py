#
# media-tools
# Copyright (C) 2019-2026 Olivier Korach
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

"""Shared fixtures of the tests.

Most of the time of the tests is spent encoding media: the tests that don't depend on a specific media file
use the small generated files of the fixtures below, which are created once per test session.
"""

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

import mediatools.utilities as util

IT_DIR = "it"


@pytest.fixture(scope="session", autouse=True)
def clean_it_directory() -> Iterator[None]:
    """The tests generate files next to their input files in the it directory: remove them at the end of the session"""
    before = set(os.listdir(IT_DIR)) if os.path.isdir(IT_DIR) else set()
    yield
    if os.path.isdir(IT_DIR):
        for name in set(os.listdir(IT_DIR)) - before:
            path = Path(IT_DIR) / name
            if path.is_file():
                path.unlink()


def _ffmpeg(*args: str) -> None:
    subprocess.run([util.get_ffmpeg(), "-v", "error", "-y", *args], check=True)


def _make_video(path: Path, duration: float) -> str:
    """Generates a 320x180 25 fps h264 video with an aac audio track"""
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        f"testsrc=size=320x180:rate=25:duration={duration}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={duration}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(path),
    )
    return str(path)


@pytest.fixture(scope="session")
def short_video(tmp_path_factory: pytest.TempPathFactory) -> str:
    """A 1.5 seconds video with an audio track, generated in a fraction of a second"""
    return _make_video(tmp_path_factory.mktemp("media") / "short-video.mp4", 1.5)


@pytest.fixture(scope="session")
def video_5s(tmp_path_factory: pytest.TempPathFactory) -> str:
    """A 5 seconds video with an audio track, for the tests that cut time ranges"""
    return _make_video(tmp_path_factory.mktemp("media") / "video-5s.mp4", 5)


@pytest.fixture(scope="session")
def short_audio(tmp_path_factory: pytest.TempPathFactory) -> str:
    """A 40 seconds excerpt of the test song, to test the audio analysis without analyzing a whole song"""
    path = tmp_path_factory.mktemp("media") / "short-audio.mp3"
    _ffmpeg("-ss", "30", "-t", "40", "-i", os.path.join(IT_DIR, "seal.mp3"), "-c", "copy", str(path))
    return str(path)
