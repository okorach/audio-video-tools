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

"""Tests that the files generated from a source file, or modified in place, have the creation and modification dates of the source file"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import pytest
from mediatools import audio_normalize
import mediatools.audiofile as audio
from mediatools import fix_mp3_meta
import mediatools.imagefile as image
from mediatools import metacopy
from mediatools import pdf_compress
from mediatools import pdf_merge
from mediatools import pdf_split
import mediatools.utilities as util
import mediatools.videofile as video
from collections.abc import Callable

OLD_DATE = datetime(2020, 5, 17, 10, 30, 0)
OLD_DATE_STR = OLD_DATE.strftime(util.EXIF_DATE_FMT)


def set_dates(path: str) -> str:
    """Gives the old date to the modification date and, on Windows, to the creation date of the file"""
    if os.name == "nt":
        subprocess.run(
            [util.get_exiftool(), "-P", "-overwrite_original", f"-FileCreateDate={OLD_DATE_STR}", str(path)], capture_output=True, check=True
        )
    os.utime(path, (OLD_DATE.timestamp(), OLD_DATE.timestamp()))
    return str(path)


def dates(path: str) -> tuple[datetime, datetime | None]:
    """The modification date and, on Windows, the creation date of a file"""
    stat = os.stat(path)
    created = datetime.fromtimestamp(getattr(stat, "st_birthtime", stat.st_ctime)) if os.name == "nt" else None
    return datetime.fromtimestamp(stat.st_mtime), created


def assert_old_dates(path: str) -> None:
    modified, created = dates(path)
    assert abs((modified - OLD_DATE).total_seconds()) < 2, f"{path} modified {modified}"
    if created is not None:
        assert abs((created - OLD_DATE).total_seconds()) < 2, f"{path} created {created}"


@pytest.fixture
def old_video(short_video: str, tmp_path: Path) -> str:
    return set_dates(shutil.copy(short_video, tmp_path / "old.mp4"))


@pytest.fixture
def old_audio(short_audio: str, tmp_path: Path) -> str:
    return set_dates(shutil.copy(short_audio, tmp_path / "old.mp3"))


# ------------------------------------------------ Helpers


def test_preserve_dates(old_video: str) -> None:
    time_before = datetime.now()
    with metacopy.preserve_dates(old_video):
        Path(old_video).write_bytes(Path(old_video).read_bytes() + b"x")
        assert dates(old_video)[0] >= time_before.replace(microsecond=0)
    assert_old_dates(old_video)


def test_preserve_dates_of_a_file_deleted_or_missing(tmp_path: Path) -> None:
    gone = tmp_path / "gone.txt"
    gone.write_text("x")
    with metacopy.preserve_dates(str(gone)):
        gone.unlink()
    with metacopy.preserve_dates(str(tmp_path / "missing.txt")):
        pass


def test_keeps_dates_decorator(old_video: str) -> None:
    @metacopy.keeps_dates
    def modify(filename: str, content: bytes) -> str:
        Path(filename).write_bytes(content)
        return "done"

    assert modify(old_video, b"new content") == "done"
    assert Path(old_video).read_bytes() == b"new content"
    assert_old_dates(old_video)


def test_copy_dates_to_any_file(old_video: str, tmp_path: Path) -> None:
    other = tmp_path / "other.txt"
    other.write_text("not a media file")
    metacopy.copy_date_and_geotag(old_video, str(other))
    assert_old_dates(str(other))


# ------------------------------------------------ Tools that run ffmpeg


@pytest.mark.parametrize(
    "generate",
    [
        lambda f: video.rotate(f, hw_accel="off"),
        lambda f: video.reverse(f, hw_accel="off"),
        lambda f: video.speed(f, 2, hw_accel="off"),
        lambda f: video.volume(f, 2, hw_accel="off"),
        lambda f: video.VideoFile(f).encode(target_file=f.replace("old.mp4", "encoded.mp4"), vcodec="x265", hw_accel="off"),
    ],
    ids=["rotate", "reverse", "speed", "volume", "encode"],
)
def test_ffmpeg_tools_keep_the_dates(old_video: str, generate: Callable[[str], str]) -> None:
    out = generate(old_video)
    assert out != old_video
    assert_old_dates(out)


def test_rotate_keep_name_keeps_the_dates(old_video: str) -> None:
    out = video.rotate(old_video, keep_name=True)
    assert out == old_video
    assert_old_dates(old_video)
    assert_old_dates(old_video.replace("old.mp4", "old.before_r90.mp4"))


def test_scale_image_keeps_the_dates(tmp_path: Path) -> None:
    # An image without EXIF date: the dates of the file are the ones of the image
    photo = str(tmp_path / "photo.jpg")
    subprocess.run([util.get_ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=640x480", "-frames:v", "1", photo], check=True)
    set_dates(photo)
    assert_old_dates(image.ImageFile(photo).scale(320, -1))
    assert_old_dates(image.ImageFile(photo).scale(-1, -1))  # Copy of the image


# ------------------------------------------------ Tools modifying the files in place


def test_audio_set_tag_keeps_the_dates(old_audio: str) -> None:
    audio.AudioFile(old_audio).set_tag("title", "A new title")
    assert audio.AudioFile(old_audio).get_a_tag("title").first == "A new title"
    assert_old_dates(old_audio)


def test_fix_mp3_meta_keeps_the_dates(old_audio: str) -> None:
    fix_mp3_meta.write_tags(old_audio, artist="Artist", title="Title", album="Album", track=1, year=2020)
    assert fix_mp3_meta.read_existing_tags(old_audio)[:2] == ("Artist", "Title")
    assert_old_dates(old_audio)


def test_audio_normalize_keeps_the_dates(old_audio: str) -> None:
    tags = audio_normalize.AudioTags(artist="Artist", title="Title", album="Album")
    audio_normalize.write_tags(old_audio, tags)
    assert_old_dates(old_audio)


# ------------------------------------------------ PDF tools (Ghostscript is mocked: it generates the output files)


@pytest.fixture
def old_pdfs(tmp_path: Path) -> list[str]:
    pdfs = []
    for name in ("a.pdf", "b.pdf"):
        (tmp_path / name).write_bytes(b"%PDF-1.4 " + name.encode())
        pdfs.append(set_dates(tmp_path / name))
    return pdfs


def fake_ghostscript(cmd: str, **_: object) -> subprocess.CompletedProcess:
    """Generates the files that Ghostscript would generate"""
    output = next(a for a in cmd if str(a).startswith("-sOutputFile=")).split("=", 1)[1]
    if "%" in output:
        for page in (1, 2):
            Path(output % page).write_bytes(b"%PDF-1.4 page")
    else:
        Path(output).write_bytes(b"%PDF-1.4 generated")
    return subprocess.CompletedProcess(cmd, 0)


def test_pdf_compress_keeps_the_dates(old_pdfs: list[str], tmp_path: Path) -> None:
    with patch.object(subprocess, "run", side_effect=fake_ghostscript), patch.object(pdf_compress, "find_ghostscript", return_value="gs"):
        out = pdf_compress.compress(old_pdfs[0], str(tmp_path / "compressed.pdf"))
        assert_old_dates(out)
        out = pdf_compress.compress(old_pdfs[1])
    assert out == old_pdfs[1]
    assert_old_dates(old_pdfs[1])
    assert_old_dates(pdf_compress.original_file(old_pdfs[1]))


def test_pdf_merge_keeps_the_dates(old_pdfs: list[str], tmp_path: Path) -> None:
    with patch.object(subprocess, "run", side_effect=fake_ghostscript), patch.object(pdf_merge, "find_ghostscript", return_value="gs"):
        out = pdf_merge.merge(old_pdfs, str(tmp_path / "merged.pdf"))
    assert_old_dates(out)


def test_pdf_split_keeps_the_dates(old_pdfs: list[str]) -> None:
    with (
        patch.object(subprocess, "run", side_effect=fake_ghostscript),
        patch.object(pdf_split, "find_ghostscript", return_value="gs"),
        patch.object(pdf_split, "page_count", return_value=2),
    ):
        assert pdf_split.split(old_pdfs[0]) == 2
    pages = sorted(Path(old_pdfs[0]).parent.glob("a.page_*.pdf"))
    assert len(pages) == 2
    for page in pages:
        assert_old_dates(str(page))
