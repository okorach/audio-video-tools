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

import shutil
from datetime import datetime
from pathlib import Path

import pytest

from mediatools import datefixer
import mediatools.videofile as video


@pytest.mark.parametrize("folder", ["plain", "Vidéos/Films montés"])
def test_absolute_date_of_a_file_whose_path_has_accents(short_video: str, tmp_path: Path, folder: str) -> None:
    """The absolute date is set on files whose path has accents (exiftool needs the file names as UTF-8)"""
    target = tmp_path / folder
    target.mkdir(parents=True)
    file = str(shutil.copy(short_video, target / "2026 - Haarlem_2pistes.mp4"))
    assert datefixer.change_file_date(file, "absolute", "2020-01-02 03:04:05") == (file, True)
    assert video.get_creation_date(file) == datetime(2020, 1, 2, 3, 4, 5)
