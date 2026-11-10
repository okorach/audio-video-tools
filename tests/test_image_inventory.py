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

"""Tests of the photo inventory tool (imagetool inventory)"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import csv
import os
import shutil
import sys
from pathlib import Path
from unittest import mock
from unittest.mock import patch

import pytest

import mediatools.utilities as util
from mediatools import image_inventory, tools

REAL_IMAGE = os.path.join("it", "img-640x480.jpg")


class FakeExifToolHelper:
    """A fake ExifToolHelper that returns canned EXIF data instead of running exiftool"""

    def __init__(self, data: dict) -> None:
        """Creates a fake ExifToolHelper that returns data for any file given to get_metadata()"""
        self.data = data

    def get_metadata(self, _filename: str) -> list[dict]:
        """Returns the canned EXIF data, as exiftool would for a single file"""
        return [self.data]


def test_get_dimensions_falls_back_across_tags() -> None:
    """The dimensions are read from the first pair of tags that is present"""
    assert image_inventory._get_dimensions({"File:ImageWidth": 640, "File:ImageHeight": 480}) == (640, 480)
    assert image_inventory._get_dimensions({"EXIF:ExifImageWidth": 800, "EXIF:ExifImageHeight": 600}) == (800, 600)
    assert image_inventory._get_dimensions({"Composite:ImageSize": "1024 768"}) == (1024, 768)
    assert image_inventory._get_dimensions({}) == (None, None)


def test_get_gps_returns_lat_lon_and_altitude() -> None:
    """The GPS coordinates are read when present, None values otherwise"""
    assert image_inventory._get_gps({"Composite:GPSLatitude": "10.5", "Composite:GPSLongitude": "-20.25", "Composite:GPSAltitude": 100}) == (
        10.5,
        -20.25,
        100.0,
    )
    assert image_inventory._get_gps({}) == (None, None, None)


def test_get_device_combines_make_and_model() -> None:
    """The device is the make and the model, trimmed of extra whitespace"""
    assert image_inventory._get_device({"EXIF:Make": "Canon", "EXIF:Model": "EOS R5"}) == "Canon EOS R5"
    assert image_inventory._get_device({"EXIF:Make": "Canon"}) == "Canon"
    assert image_inventory._get_device({}) is None


def test_get_date_taken_prefers_date_time_original() -> None:
    """The date taken is read from DateTimeOriginal, falling back to CreateDate, ignoring invalid or epoch dates"""
    taken = image_inventory._get_date_taken({"EXIF:DateTimeOriginal": "2020:06:15 10:30:00", "EXIF:CreateDate": "2020:06:14 10:30:00"})
    assert taken.strftime(image_inventory.DATE_FMT) == "2020-06-15 10:30:00"
    assert image_inventory._get_date_taken({"EXIF:CreateDate": "2020:06:14 10:30:00"}).day == 14
    assert image_inventory._get_date_taken({"EXIF:DateTimeOriginal": "0000:00:00 00:00:00"}) is None
    assert image_inventory._get_date_taken({}) is None


def test_file_dates_returns_size_and_formatted_dates(tmp_path: Path) -> None:
    """The file size and dates are read with os.stat and the dates formatted"""
    f = tmp_path / "photo.jpg"
    f.write_bytes(b"0123456789")
    size, created, modified = image_inventory._file_dates(str(f))
    assert size == 10
    assert created is not None
    assert modified is not None


def test_file_dates_handles_missing_file() -> None:
    """A missing file returns None values instead of raising"""
    assert image_inventory._file_dates("does-not-exist.jpg") == (None, None, None)


def test_photo_row_matches_the_csv_header_order(tmp_path: Path) -> None:
    """A photo row has one value per column of the CSV header, in order, built from its EXIF data and its file info"""
    f = tmp_path / "photo.jpg"
    f.write_bytes(b"0123456789")
    exif_data = {
        "File:ImageWidth": 640,
        "File:ImageHeight": 480,
        "EXIF:DateTimeOriginal": "2020:06:15 10:30:00",
        "Composite:GPSLatitude": "10.5",
        "Composite:GPSLongitude": "-20.25",
        "EXIF:Make": "Canon",
        "EXIF:Model": "EOS R5",
        "EXIF:ISO": 100,
    }
    row = image_inventory.photo_row(FakeExifToolHelper(exif_data), str(f))
    assert len(row) == len(image_inventory.CSV_HEADER)
    values = dict(zip(image_inventory.CSV_HEADER, row, strict=True))
    assert values["full_path"] == os.path.abspath(str(f))
    assert values["file_name"] == "photo.jpg"
    assert values["size_bytes"] == 10
    assert values["width"] == 640
    assert values["height"] == 480
    assert values["date_taken"] == "2020-06-15 10:30:00"
    assert values["gps_latitude"] == 10.5
    assert values["device"] == "Canon EOS R5"
    assert values["iso"] == 100


def test_chunks_splits_preserving_order() -> None:
    """The files are split into chunks of (almost) equal size, preserving their order"""
    files = [str(i) for i in range(10)]
    chunks = image_inventory._chunks(files, 3)
    assert [f for chunk in chunks for f in chunk] == files
    assert len(chunks) <= 3


def test_progress_logs_every_period_and_on_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    """The progress is logged once the period has elapsed, and always for the last photo, even if the period has not elapsed"""
    times = iter([0, 5, 11, 11.5])
    monkeypatch.setattr(image_inventory.time, "monotonic", lambda: next(times))
    with mock.patch.object(image_inventory.log.logger, "info") as log_info:
        done = image_inventory._progress_logger(3)
        done()  # elapsed = 5, not logged
        done()  # elapsed = 11, logged
        done()  # elapsed = 0.5, but last photo, logged
    assert log_info.call_count == 2
    assert log_info.call_args_list[-1].args[1:] == (3, 3, 100.0)


pytestmark = pytest.mark.skipif(shutil.which(util.get_exiftool()) is None, reason="exiftool is not installed")


def test_inventory_writes_a_csv_with_one_row_per_photo(tmp_path: Path) -> None:
    """Inventorying real photos writes a CSV file with the header and one row per photo, with the real dimensions and size"""
    out_file = str(tmp_path / "inventory.csv")
    nb_photos = image_inventory.inventory([REAL_IMAGE], out_file, max_workers=2)
    assert nb_photos == 1
    with open(out_file, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == list(image_inventory.CSV_HEADER)
    assert len(rows) == 2
    values = dict(zip(image_inventory.CSV_HEADER, rows[1], strict=True))
    assert values["file_name"] == "img-640x480.jpg"
    assert values["width"] == "640"
    assert values["height"] == "480"
    assert int(values["size_bytes"]) == Path(REAL_IMAGE).stat().st_size


def test_inventory_handles_several_photos_across_threads(tmp_path: Path) -> None:
    """Several photos are all inventoried, whichever thread (and chunk) they end up processed by"""
    photos = [REAL_IMAGE, os.path.join("it", "img-large.jpg"), os.path.join("it", "img-superwide.jpg")]
    out_file = str(tmp_path / "inventory.csv")
    nb_photos = image_inventory.inventory(photos, out_file, max_workers=2)
    assert nb_photos == 3
    with open(out_file, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 4
    file_names = {row[1] for row in rows[1:]}
    assert file_names == {"img-640x480.jpg", "img-large.jpg", "img-superwide.jpg"}


def test_main_inventories_photos_given_in_dash_i(tmp_path: Path) -> None:
    """imagetool inventory -i reads the photos given and writes the CSV file"""
    out_file = str(tmp_path / "out.csv")
    with patch.object(sys, "argv", ["imagetool", "inventory", "-i", REAL_IMAGE, "-o", out_file]):
        tools.imagetool()
    assert os.path.isfile(out_file)
    with open(out_file, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2


def test_main_defaults_the_output_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """imagetool inventory defaults its output file to photo-inventory.csv in the current directory"""
    monkeypatch.chdir(tmp_path)
    with patch.object(sys, "argv", ["imagetool", "inventory", "-i", os.path.abspath(REAL_IMAGE)]):
        tools.imagetool()
    assert (tmp_path / image_inventory.DEFAULT_OUTPUT).is_file()
