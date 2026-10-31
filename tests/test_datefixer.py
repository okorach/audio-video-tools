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

"""Tests of the datefixer tool"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import shutil
from datetime import datetime
from pathlib import Path

import pytest

from mediatools import datefixer
import mediatools.imagefile as image
import mediatools.videofile as video
from mediatools import metacopy, renamer


@pytest.mark.parametrize("folder", ["plain", "Vidéos/Films montés"])
def test_absolute_date_of_a_file_whose_path_has_accents(short_video: str, tmp_path: Path, folder: str) -> None:
    """The absolute date is set on files whose path has accents (exiftool needs the file names as UTF-8)"""
    target = tmp_path / folder
    target.mkdir(parents=True)
    file = str(shutil.copy(short_video, target / "2026 - Haarlem_2pistes.mp4"))
    assert datefixer.change_file_date(file, "absolute", "2020-01-02 03:04:05") == (file, True)
    assert video.get_creation_date(file) == datetime(2020, 1, 2, 3, 4, 5)


@pytest.fixture
def accent_folder(tmp_path: Path) -> Path:
    """A folder whose path has accents"""
    folder = tmp_path / "Vidéos" / "Films montés"
    folder.mkdir(parents=True)
    return folder


def test_exif_operations_on_a_path_with_accents(accent_folder: Path, short_video: str) -> None:
    """The exiftool operations find the files whose path has accents"""
    date = datetime(2021, 6, 7, 8, 9, 10)
    photo = image.ImageFile(str(shutil.copy("it/img-640x480.jpg", accent_folder / "photo.jpg")))
    photo.set_exif_creation_date(date)
    photo.set_exif_gps_coordinates(48.5, -2.25)
    assert float(photo.get_exif_data(force=True)["Composite:GPSLatitude"]) == pytest.approx(48.5)
    data = renamer.get_file_data(photo.filename)
    assert data is not None
    assert data["creation_date"] == date
    clip = video.VideoFile(str(shutil.copy(short_video, accent_folder / "clip.mp4")))
    clip.set_creation_date(date)
    assert video.get_creation_date(clip.filename) == date
    video.get_exif(clip.filename)


def test_metacopy_on_paths_with_accents(accent_folder: Path) -> None:
    """The dates and the geotagging are copied to and restored on files whose path has accents"""
    source = image.ImageFile(str(shutil.copy("it/img-640x480.jpg", accent_folder / "source.jpg")))
    source.set_exif_gps_coordinates(48.5, -2.25)
    target = accent_folder / "copié.jpg"
    shutil.copy("it/img-1770x1291.jpg", target)
    stat = target.stat()
    metacopy.copy_date_and_geotag(source.filename, str(target))
    assert float(image.ImageFile(str(target)).get_exif_data(force=True)["Composite:GPSLatitude"]) == pytest.approx(48.5)
    metacopy.restore_dates(str(target), stat)
