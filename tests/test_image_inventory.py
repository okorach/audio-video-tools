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
import time
import types
from datetime import datetime
from pathlib import Path
from unittest import mock
from unittest.mock import patch

import pytest
from PIL import Image

import mediatools.utilities as util
from mediatools import image_inventory, tools

REAL_IMAGE = os.path.join("it", "img-640x480.jpg")
OTHER_IMAGE = os.path.join("it", "img-superwide.jpg")


def fake_exiftool(data: dict) -> types.SimpleNamespace:
    """Returns a fake ExifToolHelper that returns data (as a single-element list) for any file given to get_metadata()"""
    return types.SimpleNamespace(get_metadata=lambda _filename: [data])


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


def test_date_from_filename_guesses_the_date_and_time_when_encoded() -> None:
    """The date (and time, when encoded) is guessed from common camera/phone file name patterns"""
    assert image_inventory._date_from_filename("IMG_20180706_125922.jpg") == "2018-07-06 12:59:22"
    assert image_inventory._date_from_filename("PXL_20210101_123456.jpg") == "2021-01-01 12:34:56"
    assert image_inventory._date_from_filename("20130804_174038.jpg") == "2013-08-04 17:40:38"
    assert image_inventory._date_from_filename("25-12-2011 16-46-10_0021.JPG") == "2011-12-25 16:46:10"
    assert image_inventory._date_from_filename("2014-07-20 20.19.20.jpg") == "2014-07-20 20:19:20"
    assert image_inventory._date_from_filename("signal-2020-01-01-123456.jpg") == "2020-01-01 12:34:56"
    assert image_inventory._date_from_filename("IMG-20200101-WA0001.jpg") == "2020-01-01 00:00:00"


def test_date_from_filename_returns_none_when_nothing_is_encoded_or_invalid() -> None:
    """A descriptive file name, or one with an invalid date embedded, guesses nothing rather than a wrong date"""
    assert image_inventory._date_from_filename("Chicago 2018 55.jpg") is None
    assert image_inventory._date_from_filename("DSC_0001.jpg") is None
    assert image_inventory._date_from_filename("HPIM00001234.jpg") is None  # 00001234 is not a valid YYYYMMDD


def test_resolve_date_taken_prefers_exif_then_filename_then_file_dates() -> None:
    """The EXIF date wins when there is one; otherwise the file name is tried, then the file's own dates"""
    exif_date = datetime.strptime("2020-06-15 10:30:00", image_inventory.DATE_FMT)
    assert image_inventory._resolve_date_taken(exif_date, "IMG_20180706_125922.jpg", "2019-01-01 00:00:00", None) == "2020-06-15 10:30:00"
    assert image_inventory._resolve_date_taken(None, "IMG_20180706_125922.jpg", "2019-01-01 00:00:00", None) == "2018-07-06 12:59:22"
    assert image_inventory._resolve_date_taken(None, "Chicago 2018 55.jpg", "2019-01-01 00:00:00", None) == "2019-01-01 00:00:00"
    assert image_inventory._resolve_date_taken(None, "Chicago 2018 55.jpg", None, "2019-02-02 00:00:00") == "2019-02-02 00:00:00"
    assert image_inventory._resolve_date_taken(None, "Chicago 2018 55.jpg", None, None) is None


def test_parse_http_date_reformats_to_date_fmt() -> None:
    """An HTTP date header (eg a Last-Modified one) is reformatted to DATE_FMT"""
    assert image_inventory._parse_http_date("Wed, 04 Aug 2013 17:40:38 GMT") == "2013-08-04 17:40:38"
    assert image_inventory._parse_http_date(None) is None
    assert image_inventory._parse_http_date("not a date") is None


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
    row = image_inventory.photo_row(fake_exiftool(exif_data), str(f))
    assert len(row) == len(image_inventory.PHOTO_CSV_HEADER)
    values = dict(zip(image_inventory.PHOTO_CSV_HEADER, row, strict=True))
    assert values["full_path"] == os.path.abspath(str(f))
    assert values["file_name"] == "photo.jpg"
    assert values["size_bytes"] == 10
    assert values["width"] == 640
    assert values["height"] == 480
    assert values["date_taken"] == "2020-06-15 10:30:00"
    assert values["gps_latitude"] == 10.5
    assert values["device"] == "Canon EOS R5"
    assert values["iso"] == 100
    assert values["fingerprint"] is None  # Not a real image, so it can't be read as one


def test_fingerprint_is_identical_for_a_renamed_copy(tmp_path: Path) -> None:
    """The fingerprint only depends on the pixels, so a byte-for-byte copy under a different name has the same one"""
    copy = tmp_path / "same-photo-different-name.jpg"
    copy.write_bytes(Path(REAL_IMAGE).read_bytes())
    assert image_inventory.compute_fingerprint(str(copy)) == image_inventory.compute_fingerprint(REAL_IMAGE)


def test_fingerprint_returns_none_for_a_file_that_is_not_an_image(tmp_path: Path) -> None:
    """A file that can't be read as an image has no fingerprint, instead of raising"""
    f = tmp_path / "not-a-photo.jpg"
    f.write_bytes(b"this is not a jpeg")
    assert image_inventory.compute_fingerprint(str(f)) is None


def test_fingerprint_logs_the_file_name_of_a_very_large_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pillow's own DecompressionBombWarning doesn't name the file: a very large image logs a warning naming it"""
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)  # Any real photo now exceeds the limit
    with mock.patch.object(image_inventory.log.logger, "warning") as log_warning:
        image_inventory.compute_fingerprint(REAL_IMAGE)
    assert any(REAL_IMAGE in call.args for call in log_warning.call_args_list)


def test_fingerprint_from_bytes_matches_the_file_based_one() -> None:
    """compute_fingerprint_from_bytes() computes the exact same fingerprint as compute_fingerprint() for the same pixels,
    since it shares the same underlying logic, just fed from in-memory bytes (as downloaded from Google Photos) instead
    of a local file"""
    data = Path(REAL_IMAGE).read_bytes()
    assert image_inventory.compute_fingerprint_from_bytes(data, "context.jpg") == image_inventory.compute_fingerprint(REAL_IMAGE)


def test_fingerprint_from_bytes_returns_none_for_bytes_that_are_not_an_image() -> None:
    """Bytes that can't be read as an image have no fingerprint, instead of raising"""
    assert image_inventory.compute_fingerprint_from_bytes(b"not an image", "context.jpg") is None


def test_fingerprint_is_closer_for_a_resized_copy_than_for_a_different_photo(tmp_path: Path) -> None:
    """A resized copy of a photo keeps a fingerprint close to the original one, much closer than an unrelated photo"""
    resized = tmp_path / "resized.jpg"
    with Image.open(REAL_IMAGE) as img:
        img.resize((img.width // 2, img.height // 2)).save(resized)
    original_fp = image_inventory.compute_fingerprint(REAL_IMAGE)
    resized_fp = image_inventory.compute_fingerprint(str(resized))
    other_fp = image_inventory.compute_fingerprint(OTHER_IMAGE)
    assert image_inventory.hamming_distance(original_fp, resized_fp) < image_inventory.hamming_distance(original_fp, other_fp)


def test_fingerprint_is_closer_for_a_cropped_copy_than_for_a_different_photo(tmp_path: Path) -> None:
    """A photo cropped a bit keeps a fingerprint close to the original one, much closer than an unrelated photo"""
    cropped = tmp_path / "cropped.jpg"
    with Image.open(REAL_IMAGE) as img:
        img.crop((10, 10, img.width - 10, img.height - 10)).save(cropped)
    original_fp = image_inventory.compute_fingerprint(REAL_IMAGE)
    cropped_fp = image_inventory.compute_fingerprint(str(cropped))
    other_fp = image_inventory.compute_fingerprint(OTHER_IMAGE)
    assert image_inventory.hamming_distance(original_fp, cropped_fp) < image_inventory.hamming_distance(original_fp, other_fp)


def test_hamming_distance_counts_the_differing_bits() -> None:
    """The hamming distance is the number of bits that differ, None if a fingerprint is missing or they are not comparable"""
    assert image_inventory.hamming_distance("ff", "ff") == 0
    assert image_inventory.hamming_distance("ff", "00") == 8
    assert image_inventory.hamming_distance(None, "ff") is None
    assert image_inventory.hamming_distance("ff", None) is None
    assert image_inventory.hamming_distance("ff", "fff") is None


def _row(**values: object) -> list[object]:
    """Returns a row of PHOTO_CSV_HEADER columns, defaulting every column not given in values to None"""
    return [values.get(column) for column in image_inventory.PHOTO_CSV_HEADER]


def _csv_row(**values: str) -> dict[str, str]:
    """Returns a dict row of CSV_HEADER columns, as read back by csv.DictReader, defaulting every column not given to ''"""
    return {column: str(values.get(column, "")) for column in image_inventory.CSV_HEADER}


def test_similarity_is_high_when_fingerprint_and_metadata_all_match() -> None:
    """2 photos with an identical fingerprint and matching metadata get a high duplicate likelihood"""
    common = {
        "fingerprint": "ff00ff00",
        "size_bytes": 12345,
        "width": 640,
        "height": 480,
        "date_taken": "2020-06-15 10:30:00",
        "device": "Canon EOS R5",
        "gps_latitude": 10.5,
        "gps_longitude": -20.25,
    }
    assert image_inventory._similarity(_row(**common), _row(**common)) == 100


def test_similarity_ignores_criteria_missing_on_either_photo() -> None:
    """Metadata missing on either photo is not counted against the likelihood, it is simply ignored"""
    row_a = _row(fingerprint="ff00ff00", size_bytes=12345)
    row_b = _row(fingerprint="ff00ff00")  # No size_bytes at all
    assert image_inventory._similarity(row_a, row_b) == 100


def test_similarity_decreases_with_the_fingerprint_hamming_distance() -> None:
    """The fingerprint contribution decreases as the 2 fingerprints get further apart"""
    close = image_inventory._similarity(_row(fingerprint="00000000"), _row(fingerprint="00000001"))
    far = image_inventory._similarity(_row(fingerprint="00000000"), _row(fingerprint="ffffffff"))
    assert close > far


def test_similarity_returns_none_when_not_enough_criteria_are_applicable() -> None:
    """2 photos with no fingerprint and a single weak matching criterion can't say much about being duplicates"""
    assert image_inventory._similarity(_row(device="Canon"), _row(device="Canon")) is None
    assert image_inventory._similarity(_row(), _row()) is None


def test_duplicate_candidates_groups_rows_sharing_size_date_or_fingerprint_prefix() -> None:
    """Rows sharing an exact size, an exact date taken, or a fingerprint prefix become candidate pairs, unrelated rows don't"""
    rows = [
        _row(size_bytes=100),
        _row(size_bytes=100),
        _row(date_taken="2020-06-15 10:30:00"),
        _row(date_taken="2020-06-15 10:30:00"),
        _row(fingerprint="ff00ff00"),
        _row(fingerprint="ff001234"),
        _row(size_bytes=200),
    ]
    pairs = image_inventory._duplicate_candidates(rows)
    assert (0, 1) in pairs
    assert (2, 3) in pairs
    assert (4, 5) in pairs
    assert not any(6 in pair for pair in pairs)


def test_add_duplicate_likelihood_picks_the_best_match_and_appends_columns() -> None:
    """Each row is amended with the likelihood and the full path of its most likely duplicate among the candidates"""
    rows = [
        _row(full_path="a.jpg", fingerprint="00000000"),
        _row(full_path="b.jpg", fingerprint="00000001"),  # Close to a.jpg
        _row(full_path="c.jpg", fingerprint="ffffffff"),  # Far from both
    ]
    image_inventory.add_duplicate_likelihood(rows)
    for row in rows:
        assert len(row) == len(image_inventory.CSV_HEADER)
    values_a = dict(zip(image_inventory.CSV_HEADER, rows[0], strict=True))
    assert values_a["duplicate_of"] == "b.jpg"
    assert values_a["duplicate_likelihood"] > 0


def test_add_duplicate_likelihood_leaves_empty_values_when_no_duplicate_is_found() -> None:
    """A photo with no candidate duplicate gets empty duplicate_likelihood and duplicate_of columns"""
    rows = [_row(full_path="a.jpg", device="Canon")]
    image_inventory.add_duplicate_likelihood(rows)
    values = dict(zip(image_inventory.CSV_HEADER, rows[0], strict=True))
    assert values["duplicate_likelihood"] == ""
    assert values["duplicate_of"] == ""


def test_write_then_read_inventory_csv_roundtrips_the_photo_columns(tmp_path: Path) -> None:
    """A CSV written by _write_csv() can be read back by _read_inventory_csv(), ignoring the duplicate columns"""
    rows = [_row(full_path="a.jpg", file_name="a.jpg", size_bytes=10, width=640, height=480, gps_latitude=10.5, gps_longitude=-20.25)]
    image_inventory.add_duplicate_likelihood(rows)
    out_file = str(tmp_path / "inventory.csv")
    image_inventory._write_csv(rows, out_file)
    read_back = image_inventory._read_inventory_csv(out_file)
    assert len(read_back) == 1
    values = dict(zip(image_inventory.PHOTO_CSV_HEADER, read_back[0], strict=True))
    assert values["full_path"] == "a.jpg"
    assert values["size_bytes"] == "10"
    assert values["gps_latitude"] == 10.5  # Cast back to float


def test_main_computes_duplicate_likelihood_from_an_existing_csv_without_rescanning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """imagetool inventory -i <existing csv> amends it with the duplicate columns, without collecting or scanning any photo"""
    monkeypatch.setattr(image_inventory, "_collect_photos", lambda _paths: pytest.fail("Should not rescan photos from a CSV input"))
    in_file = str(tmp_path / "in.csv")
    with open(in_file, "w", newline="", encoding="utf-8") as fh:
        csv_writer = csv.writer(fh)
        csv_writer.writerow(image_inventory.PHOTO_CSV_HEADER)
        csv_writer.writerow(_row(full_path="a.jpg", file_name="a.jpg", fingerprint="00000000"))
        csv_writer.writerow(_row(full_path="b.jpg", file_name="b.jpg", fingerprint="00000001"))
    with patch.object(sys, "argv", ["imagetool", "inventory", "-i", in_file]):
        tools.imagetool()
    with open(in_file, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == list(image_inventory.CSV_HEADER)
    values_a = dict(zip(image_inventory.CSV_HEADER, rows[1], strict=True))
    assert values_a["duplicate_of"] == "b.jpg"


def test_main_csv_input_defaults_the_output_to_the_input_file(tmp_path: Path) -> None:
    """Without -o, a CSV input is amended in place rather than written to the default output file"""
    in_file = str(tmp_path / "in.csv")
    with open(in_file, "w", newline="", encoding="utf-8") as fh:
        csv_writer = csv.writer(fh)
        csv_writer.writerow(image_inventory.PHOTO_CSV_HEADER)
        csv_writer.writerow(_row(full_path="a.jpg", file_name="a.jpg"))
    with patch.object(sys, "argv", ["imagetool", "inventory", "-i", in_file]):
        tools.imagetool()
    assert not (tmp_path / image_inventory.DEFAULT_OUTPUT).exists()


def test_is_original_filename_recognizes_common_camera_patterns() -> None:
    """Common unedited camera/phone file names are recognized as such"""
    for name in (
        "IMG_1234.jpg",
        "IMG_20180706_125922.jpg",  # Android date_time name
        "IMG_20180709_201308_HDR.jpg",  # Android date_time name, HDR suffix
        "IMG-20200101-WA0001.jpg",  # WhatsApp
        "PXL_20210101_123456.jpg",
        "PANO_20190415_103823.jpg",  # Android panorama
        "DSC_0001.jpg",
        "DSCN1234.JPG",
        "HPIM1234.jpg",  # HP camera
        "HPIM0001234.jpg",  # HP camera, with arbitrarily many digits
        "100_1234.jpg",
        "P1010001.jpg",
        "20130804_174038.jpg",  # Date_time name with no camera prefix
        "25-12-2011 16-46-10_0021.JPG",  # DD-MM-YYYY HH-MM-SS_sequence
        "2014-07-20 20.19.20.jpg",  # YYYY-MM-DD HH.MM.SS
    ):
        assert image_inventory._is_original_filename(name), name


def test_is_original_filename_rejects_descriptive_names() -> None:
    """A file name that was changed to something descriptive is not mistaken for a camera original one"""
    for name in ("Chicago 2018 55.jpg", "family-beach-trip.jpg", "vacation.png"):
        assert not image_inventory._is_original_filename(name), name


def test_size_rule_recommends_the_significantly_smaller_photo() -> None:
    """The photo whose size is below DEDUP_SIZE_RATIO_THRESHOLD of the other one is recommended for deletion"""
    assert image_inventory._size_rule(_csv_row(size_bytes="1000"), _csv_row(size_bytes="100")) == 2
    assert image_inventory._size_rule(_csv_row(size_bytes="100"), _csv_row(size_bytes="1000")) == 1


def test_size_rule_returns_none_when_sizes_are_close_or_missing() -> None:
    """The size rule is not conclusive when the sizes are close, or either is missing"""
    assert image_inventory._size_rule(_csv_row(size_bytes="1000"), _csv_row(size_bytes="950")) is None
    assert image_inventory._size_rule(_csv_row(size_bytes="1000"), _csv_row()) is None


def test_original_filename_rule_recommends_the_unedited_name() -> None:
    """The photo with a camera original file name is recommended for deletion over the one renamed descriptively"""
    original = _csv_row(file_name="IMG_1234.jpg")
    descriptive = _csv_row(file_name="Chicago 2018 55.jpg")
    assert image_inventory._original_filename_rule(original, descriptive) == 1
    assert image_inventory._original_filename_rule(descriptive, original) == 2
    assert image_inventory._original_filename_rule(original, original) is None


def test_gps_rule_recommends_the_photo_without_gps() -> None:
    """The photo missing GPS coordinates is recommended for deletion over the one that has them"""
    with_gps = _csv_row(gps_latitude="10.5")
    without_gps = _csv_row()
    assert image_inventory._gps_rule(with_gps, without_gps) == 2
    assert image_inventory._gps_rule(without_gps, with_gps) == 1
    assert image_inventory._gps_rule(with_gps, with_gps) is None


def test_in_duplicate_folder_matches_a_folder_name_containing_duplicate() -> None:
    """A folder with 'duplicate' anywhere in its name, anywhere in the path, is detected: case-insensitively (eg
    'DUpliCates'), and whether singular or plural, since it's a plain substring match, not an exact word; the file
    name itself doesn't count"""
    assert image_inventory._in_duplicate_folder(os.path.join("C:", "Photos", "Duplicates", "a.jpg"))
    assert image_inventory._in_duplicate_folder(os.path.join("C:", "Photos", "DUpliCates", "a.jpg"))
    assert image_inventory._in_duplicate_folder(os.path.join("C:", "Photos", "zzz_Duplicate Photos", "a.jpg"))
    assert not image_inventory._in_duplicate_folder(os.path.join("C:", "Photos", "2020", "duplicate.jpg"))
    assert not image_inventory._in_duplicate_folder(os.path.join("C:", "Photos", "2020", "a.jpg"))


def test_duplicate_folder_rule_recommends_the_photo_filed_as_a_duplicate() -> None:
    """The photo located in a folder whose name indicates known duplicates is recommended for deletion"""
    in_duplicates = _csv_row(full_path=os.path.join("C:", "Photos", "Duplicates", "a.jpg"))
    elsewhere = _csv_row(full_path=os.path.join("C:", "Photos", "2020", "a.jpg"))
    assert image_inventory._duplicate_folder_rule(in_duplicates, elsewhere) == 1
    assert image_inventory._duplicate_folder_rule(elsewhere, in_duplicates) == 2
    assert image_inventory._duplicate_folder_rule(in_duplicates, in_duplicates) is None


def test_in_to_sort_folder_matches_a_trier_case_and_accent_insensitively() -> None:
    """The French 'a_trier'/'a trier' ('to be sorted') folder is detected whatever its case, accent, or
    underscore/space spelling; the file name itself doesn't count, and an unrelated folder doesn't match"""
    assert image_inventory._in_to_sort_folder(os.path.join("C:", "Photos", "a_trier", "a.jpg"))
    assert image_inventory._in_to_sort_folder(os.path.join("C:", "Photos", "a trier", "a.jpg"))
    assert image_inventory._in_to_sort_folder(os.path.join("C:", "Photos", "À_Trier", "a.jpg"))
    assert image_inventory._in_to_sort_folder(os.path.join("C:", "Photos", "A TRIER", "a.jpg"))
    assert not image_inventory._in_to_sort_folder(os.path.join("C:", "Photos", "2020", "a_trier.jpg"))
    assert not image_inventory._in_to_sort_folder(os.path.join("C:", "Photos", "2020", "a.jpg"))


def test_to_sort_folder_rule_recommends_the_photo_not_yet_sorted() -> None:
    """The photo still sitting in an 'a_trier' folder is recommended for deletion"""
    to_sort = _csv_row(full_path=os.path.join("C:", "Photos", "a_trier", "a.jpg"))
    elsewhere = _csv_row(full_path=os.path.join("C:", "Photos", "2020", "a.jpg"))
    assert image_inventory._to_sort_folder_rule(to_sort, elsewhere) == 1
    assert image_inventory._to_sort_folder_rule(elsewhere, to_sort) == 2
    assert image_inventory._to_sort_folder_rule(to_sort, to_sort) is None


def test_recommend_deletion_checks_rules_in_order() -> None:
    """The duplicate-folder rule wins over every other rule when it is conclusive, and the size rule wins over the
    file name and GPS rules when it is conclusive"""
    in_duplicates = _csv_row(full_path=os.path.join("Duplicates", "a.jpg"), size_bytes="1000000")  # Much larger, but filed as a duplicate
    elsewhere = _csv_row(full_path=os.path.join("Elsewhere", "a.jpg"), size_bytes="100")
    assert image_inventory._recommend_deletion(in_duplicates, elsewhere) == 1

    row_a = _csv_row(size_bytes="1000", file_name="Chicago 2018 55.jpg", gps_latitude="10.5")
    row_b = _csv_row(size_bytes="100", file_name="IMG_1234.jpg")  # Smaller, but with an original name and no GPS
    assert image_inventory._recommend_deletion(row_a, row_b) == 2


def test_recommend_deletion_returns_none_when_no_rule_is_conclusive() -> None:
    """2 photos with nothing distinguishing them get no deletion recommendation"""
    assert image_inventory._recommend_deletion(_csv_row(), _csv_row()) is None


def test_format_size_is_human_readable() -> None:
    """_format_size() renders a file size with the appropriate unit, 'N/A' when missing"""
    assert image_inventory._format_size("500") == "500.0 B"
    assert image_inventory._format_size("2048") == "2.0 KB"
    assert image_inventory._format_size(None) == "N/A"


def test_format_gps_rounds_to_4_decimals() -> None:
    """_format_gps() renders the coordinates rounded to 4 decimal digits, 'N/A' when missing"""
    row = _csv_row(gps_latitude="10.123456", gps_longitude="-20.987654")
    assert image_inventory._format_gps(row) == "10.1235, -20.9877"
    assert image_inventory._format_gps(_csv_row()) == "N/A"


def test_dedup_pairs_sorts_by_likelihood_and_dedupes_symmetric_pairs() -> None:
    """A pair pointing at each other is only returned once, and pairs are sorted by decreasing likelihood"""
    row_a = _csv_row(full_path="a.jpg", duplicate_likelihood="80", duplicate_of="b.jpg")
    row_b = _csv_row(full_path="b.jpg", duplicate_likelihood="80", duplicate_of="a.jpg")
    row_c = _csv_row(full_path="c.jpg", duplicate_likelihood="95", duplicate_of="a.jpg")
    pairs = image_inventory._dedup_pairs([row_a, row_b, row_c])
    assert len(pairs) == 2
    assert pairs[0][0] == "95"


def test_ask_which_to_delete_reprompts_on_invalid_input(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """An answer that is not 1, 2 or 0 is rejected and the question asked again"""
    answers = iter(["bogus", "2"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert image_inventory._ask_which_to_delete(recommended=1) == 2
    assert "Please answer 1, 2, or 0" in capsys.readouterr().out


def test_ask_which_to_delete_defaults_to_recommended_on_enter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pressing Enter without typing anything answers with the recommended photo"""
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    assert image_inventory._ask_which_to_delete(recommended=2) == 2


def test_ask_which_to_delete_defaults_to_0_when_no_recommendation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pressing Enter with no recommendation at all keeps both photos"""
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    assert image_inventory._ask_which_to_delete(recommended=None) == 0


def test_delete_photo_removes_the_file(tmp_path: Path) -> None:
    """_delete_photo() removes the file from disk and returns True"""
    file_path = tmp_path / "a.jpg"
    file_path.write_bytes(b"x")
    assert image_inventory._delete_photo(str(file_path)) is True
    assert not file_path.exists()


def test_delete_photo_returns_true_when_the_file_is_already_missing(tmp_path: Path) -> None:
    """A photo already missing is reported as deleted too, so a stale entry still gets removed from the inventory"""
    assert image_inventory._delete_photo(str(tmp_path / "missing.jpg")) is True


def test_delete_photo_returns_false_when_it_exists_but_cannot_be_deleted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A photo that exists but can't be deleted (eg permission denied) is not reported as deleted"""
    file_path = tmp_path / "a.jpg"
    file_path.write_bytes(b"x")

    def _raise(_path: str) -> None:
        raise PermissionError("Access is denied")

    monkeypatch.setattr(image_inventory.os, "remove", _raise)
    assert image_inventory._delete_photo(str(file_path)) is False


def test_is_missing_detects_a_local_file_that_no_longer_exists(tmp_path: Path) -> None:
    """_is_missing() is true for a local path that doesn't exist, false for one that does"""
    file_path = tmp_path / "a.jpg"
    file_path.write_bytes(b"x")
    assert not image_inventory._is_missing(str(file_path))
    assert image_inventory._is_missing(str(tmp_path / "missing.jpg"))


def test_is_missing_ignores_google_photos_synthetic_ids() -> None:
    """_is_missing() is always false for a synthetic 'googlephotos:<id>' full_path, which has no file to check"""
    assert not image_inventory._is_missing("googlephotos:abc123")


def _write_dedup_csv(csv_file: Path, *rows: dict[str, str]) -> None:
    """Writes rows (of CSV_HEADER columns) to csv_file, as the inventory tool would"""
    with open(csv_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(image_inventory.CSV_HEADER))
        writer.writeheader()
        writer.writerows(rows)


def test_dedup_deletes_the_recommended_photo_on_enter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pressing Enter on a pair deletes the photo recommended for deletion, and rewrites the CSV without it"""
    file_a, file_b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    file_a.write_bytes(b"x" * 1000)
    file_b.write_bytes(b"x" * 100)
    csv_file = tmp_path / "inventory.csv"
    _write_dedup_csv(
        csv_file,
        _csv_row(full_path=str(file_a), file_name="a.jpg", size_bytes="1000", duplicate_likelihood="90", duplicate_of=str(file_b)),
        _csv_row(full_path=str(file_b), file_name="b.jpg", size_bytes="100", duplicate_likelihood="90", duplicate_of=str(file_a)),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    image_inventory.dedup(str(csv_file))
    assert file_a.exists()
    assert not file_b.exists()
    with open(csv_file, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [row["full_path"] for row in rows] == [str(file_a)]


def test_dedup_auto_deletes_a_100_percent_match_without_asking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A 100% likelihood pair with a recommendation is deleted automatically, without asking the user"""
    file_a, file_b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    file_a.write_bytes(b"x" * 1000)
    file_b.write_bytes(b"x" * 100)
    csv_file = tmp_path / "inventory.csv"
    _write_dedup_csv(
        csv_file,
        _csv_row(full_path=str(file_a), file_name="a.jpg", size_bytes="1000", duplicate_likelihood="100", duplicate_of=str(file_b)),
        _csv_row(full_path=str(file_b), file_name="b.jpg", size_bytes="100", duplicate_likelihood="100", duplicate_of=str(file_a)),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("Should not ask for a 100% match"))
    image_inventory.dedup(str(csv_file))
    assert file_a.exists()
    assert not file_b.exists()


def test_dedup_asks_for_a_100_percent_match_with_no_recommendation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A 100% likelihood pair is still asked about when no rule can recommend one over the other"""
    file_a, file_b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    file_a.write_bytes(b"x")
    file_b.write_bytes(b"x")
    csv_file = tmp_path / "inventory.csv"
    _write_dedup_csv(
        csv_file,
        _csv_row(full_path=str(file_a), file_name="a.jpg", duplicate_likelihood="100", duplicate_of=str(file_b)),
        _csv_row(full_path=str(file_b), file_name="b.jpg", duplicate_likelihood="100", duplicate_of=str(file_a)),
    )
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt: (asked.append(prompt), "0")[1])
    image_inventory.dedup(str(csv_file))
    assert asked
    assert file_a.exists()
    assert file_b.exists()


def test_dedup_keeps_both_when_answer_is_0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Answering 0 keeps both photos of a pair"""
    file_a, file_b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    file_a.write_bytes(b"x")
    file_b.write_bytes(b"x")
    csv_file = tmp_path / "inventory.csv"
    _write_dedup_csv(
        csv_file,
        _csv_row(full_path=str(file_a), file_name="a.jpg", duplicate_likelihood="60", duplicate_of=str(file_b)),
        _csv_row(full_path=str(file_b), file_name="b.jpg", duplicate_likelihood="60", duplicate_of=str(file_a)),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "0")
    image_inventory.dedup(str(csv_file))
    assert file_a.exists()
    assert file_b.exists()


def test_dedup_removes_a_missing_photo_from_the_csv_without_asking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When one photo of a pair no longer exists on disk, it is silently removed from the CSV, the other one is kept,
    and the user is never asked to choose"""
    file_a, file_b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    file_b.write_bytes(b"x")  # file_a is never created: already missing
    csv_file = tmp_path / "inventory.csv"
    _write_dedup_csv(
        csv_file,
        _csv_row(full_path=str(file_a), file_name="a.jpg", duplicate_likelihood="60", duplicate_of=str(file_b)),
        _csv_row(full_path=str(file_b), file_name="b.jpg", duplicate_likelihood="60", duplicate_of=str(file_a)),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("Should not ask when a photo is missing"))
    image_inventory.dedup(str(csv_file))
    with open(csv_file, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [row["full_path"] for row in rows] == [str(file_b)]


def test_dedup_removes_both_photos_when_both_are_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When neither photo of a pair exists on disk anymore, both are silently removed from the CSV, without asking"""
    file_a, file_b = tmp_path / "a.jpg", tmp_path / "b.jpg"  # Neither is ever created: both already missing
    csv_file = tmp_path / "inventory.csv"
    _write_dedup_csv(
        csv_file,
        _csv_row(full_path=str(file_a), file_name="a.jpg", duplicate_likelihood="60", duplicate_of=str(file_b)),
        _csv_row(full_path=str(file_b), file_name="b.jpg", duplicate_likelihood="60", duplicate_of=str(file_a)),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("Should not ask when both photos are missing"))
    image_inventory.dedup(str(csv_file))
    with open(csv_file, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert not rows


def test_dedup_does_not_treat_google_photos_ids_as_missing_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A synthetic 'googlephotos:<id>' full_path has no existence on disk to check, so it is never auto-removed as missing"""
    csv_file = tmp_path / "inventory.csv"
    _write_dedup_csv(
        csv_file,
        _csv_row(full_path="googlephotos:a", file_name="a.jpg", duplicate_likelihood="60", duplicate_of="googlephotos:b"),
        _csv_row(full_path="googlephotos:b", file_name="b.jpg", duplicate_likelihood="60", duplicate_of="googlephotos:a"),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "0")
    image_inventory.dedup(str(csv_file))
    with open(csv_file, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert {row["full_path"] for row in rows} == {"googlephotos:a", "googlephotos:b"}


def test_dedup_keeps_the_csv_row_when_deletion_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A photo that exists but can't be deleted stays in the CSV"""
    file_a, file_b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    file_a.write_bytes(b"x")
    file_b.write_bytes(b"x")
    csv_file = tmp_path / "inventory.csv"
    _write_dedup_csv(
        csv_file,
        _csv_row(full_path=str(file_a), file_name="a.jpg", duplicate_likelihood="60", duplicate_of=str(file_b)),
        _csv_row(full_path=str(file_b), file_name="b.jpg", duplicate_likelihood="60", duplicate_of=str(file_a)),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "1")
    monkeypatch.setattr(image_inventory, "_delete_photo", lambda _path: False)
    image_inventory.dedup(str(csv_file))
    with open(csv_file, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert {row["full_path"] for row in rows} == {str(file_a), str(file_b)}


def test_dedup_exits_when_csv_has_no_duplicate_likelihood_column(tmp_path: Path) -> None:
    """dedup() refuses a CSV that never had its duplicate likelihood computed"""
    csv_file = tmp_path / "inventory.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(image_inventory.PHOTO_CSV_HEADER))
        writer.writeheader()
        writer.writerow(dict.fromkeys(image_inventory.PHOTO_CSV_HEADER, ""))
    with pytest.raises(SystemExit):
        image_inventory.dedup(str(csv_file))


def test_main_dedup_requires_a_single_existing_csv(tmp_path: Path) -> None:
    """--dedup without a single existing CSV file in -i exits instead of trying to scan photos"""
    missing = str(tmp_path / "missing.csv")
    with patch.object(sys, "argv", ["imagetool", "inventory", "-i", missing, "--dedup"]), pytest.raises(SystemExit):
        tools.imagetool()


def test_main_dedup_invokes_dedup_on_the_given_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--dedup with a single existing CSV file in -i calls dedup() on it instead of the normal inventory flow"""
    csv_file = tmp_path / "inventory.csv"
    csv_file.write_text("full_path\n", encoding="utf-8")
    called = {}
    monkeypatch.setattr(image_inventory, "dedup", lambda path: called.setdefault("path", path))
    with patch.object(sys, "argv", ["imagetool", "inventory", "-i", str(csv_file), "--dedup"]):
        tools.imagetool()
    assert called["path"] == str(csv_file)


def test_main_requires_input_unless_google_or_dedup_is_given() -> None:
    """Without -i, --google or --dedup, main() exits instead of crashing trying to collect photos from nothing"""
    with patch.object(sys, "argv", ["imagetool", "inventory"]), pytest.raises(SystemExit):
        tools.imagetool()


def test_default_pictures_dir_is_the_users_pictures_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default output directory of --google is <home>/Pictures, the OS default pictures folder on Windows"""
    monkeypatch.setattr(image_inventory.os.path, "expanduser", lambda _p: os.path.join("C:", "Users", "someone"))
    assert image_inventory._default_pictures_dir() == os.path.join("C:", "Users", "someone", "Pictures")


def test_google_dimensions_returns_width_and_height() -> None:
    """The dimensions of a picked Google Photos item are read from its mediaFileMetadata, (None, None) if missing"""
    assert image_inventory._google_dimensions({"width": "640", "height": "480"}) == (640, 480)
    assert image_inventory._google_dimensions({}) == (None, None)


def test_google_device_combines_make_and_model() -> None:
    """The device of a picked Google Photos item combines its cameraMake and cameraModel"""
    assert image_inventory._google_device({"cameraMake": "Google", "cameraModel": "Pixel 5"}) == "Google Pixel 5"
    assert image_inventory._google_device({}) is None


def test_google_date_taken_parses_create_time() -> None:
    """The date taken of a picked Google Photos item is read from its createTime, None if missing or unparseable"""
    assert image_inventory._google_date_taken({"createTime": "2013-08-04T17:40:38Z"}) == "2013-08-04 17:40:38"
    assert image_inventory._google_date_taken({"createTime": "not-a-date"}) is None
    assert image_inventory._google_date_taken({}) is None


def test_google_photo_row_matches_the_csv_header_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Google Photos row has one value per column of PHOTO_CSV_HEADER, built from the Picker API item, with the
    columns the Picker API does not expose left empty"""
    item = {
        "id": "ABC123",
        "createTime": "2013-08-04T17:40:38Z",
        "mediaFile": {
            "baseUrl": "https://photos.example/base",
            "filename": "IMG_1234.jpg",
            "mediaFileMetadata": {
                "width": "640",
                "height": "480",
                "photoMetadata": {"cameraMake": "Google", "cameraModel": "Pixel 5", "isoEquivalent": 100, "apertureFNumber": 1.7},
            },
        },
    }
    monkeypatch.setattr(image_inventory.google_photos, "fetch_bytes", lambda _token, _url, _params: b"thumbnail-bytes")
    monkeypatch.setattr(image_inventory.google_photos, "fetch_size", lambda _token, _url: 54321)
    monkeypatch.setattr(image_inventory, "compute_fingerprint_from_bytes", lambda data, _context: "deadbeef" if data == b"thumbnail-bytes" else None)
    row = image_inventory.google_photo_row("token", item)
    assert len(row) == len(image_inventory.PHOTO_CSV_HEADER)
    values = dict(zip(image_inventory.PHOTO_CSV_HEADER, row, strict=True))
    assert values["full_path"] == "googlephotos:ABC123"
    assert values["file_name"] == "IMG_1234.jpg"
    assert values["size_bytes"] == 54321
    assert values["width"] == 640
    assert values["height"] == 480
    assert values["fingerprint"] == "deadbeef"
    assert values["date_taken"] == "2013-08-04 17:40:38"
    assert values["device"] == "Google Pixel 5"
    assert values["iso"] == 100
    assert values["aperture"] == 1.7
    assert values["gps_latitude"] is None
    assert values["lens_model"] is None


def test_google_photo_row_falls_back_to_the_filename_date_when_there_is_no_create_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a createTime, the date guessed from the file name is used, without even checking the Last-Modified header"""
    item = {"id": "X", "mediaFile": {"baseUrl": "https://photos.example/base", "filename": "IMG_20180706_125922.jpg"}}
    monkeypatch.setattr(image_inventory.google_photos, "fetch_bytes", lambda *_a: None)
    monkeypatch.setattr(image_inventory.google_photos, "fetch_size", lambda *_a: None)
    monkeypatch.setattr(image_inventory.google_photos, "fetch_last_modified", lambda *_a: pytest.fail("Should not be called"))
    row = image_inventory.google_photo_row("token", item)
    values = dict(zip(image_inventory.PHOTO_CSV_HEADER, row, strict=True))
    assert values["date_taken"] == "2018-07-06 12:59:22"


def test_google_photo_row_falls_back_to_the_last_modified_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a createTime or a date encoded in the file name, the Last-Modified header of the original file is used"""
    item = {"id": "X", "mediaFile": {"baseUrl": "https://photos.example/base", "filename": "vacation.jpg"}}
    monkeypatch.setattr(image_inventory.google_photos, "fetch_bytes", lambda *_a: None)
    monkeypatch.setattr(image_inventory.google_photos, "fetch_size", lambda *_a: None)
    monkeypatch.setattr(image_inventory.google_photos, "fetch_last_modified", lambda *_a: "Wed, 04 Aug 2013 17:40:38 GMT")
    row = image_inventory.google_photo_row("token", item)
    values = dict(zip(image_inventory.PHOTO_CSV_HEADER, row, strict=True))
    assert values["date_taken"] == "2013-08-04 17:40:38"


def test_google_photo_row_handles_an_item_without_a_base_url() -> None:
    """An item without mediaFile.baseUrl (should not happen, but defensively) gets no fingerprint and no size, instead of raising"""
    row = image_inventory.google_photo_row("token", {"id": "X", "mediaFile": {"filename": "x.jpg"}})
    values = dict(zip(image_inventory.PHOTO_CSV_HEADER, row, strict=True))
    assert values["fingerprint"] is None
    assert values["size_bytes"] is None


def _fake_picker_setup(monkeypatch: pytest.MonkeyPatch, items: list[dict], deleted: list[str]) -> None:
    """Monkeypatches the whole google_photos module as used by google_inventory(), with items as the picked photos"""
    monkeypatch.setattr(image_inventory.google_photos, "get_access_token", lambda: "token")
    monkeypatch.setattr(image_inventory.google_photos, "create_picker_session", lambda _token: {"id": "s1", "pickerUri": "https://pick"})
    monkeypatch.setattr(image_inventory.google_photos, "wait_for_selection", lambda _token, _session: {"id": "s1", "mediaItemsSet": True})
    monkeypatch.setattr(image_inventory.google_photos, "list_picked_media_items", lambda _token, _session_id: iter(items))
    monkeypatch.setattr(image_inventory.google_photos, "delete_picker_session", lambda _token, session_id: deleted.append(session_id))
    monkeypatch.setattr(image_inventory.google_photos, "fetch_bytes", lambda _token, _url, _params: None)
    monkeypatch.setattr(image_inventory.google_photos, "fetch_size", lambda _token, _url: None)


def test_google_inventory_writes_the_csv_and_deletes_the_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """google_inventory() lists the picked items, writes them to the CSV with their duplicate likelihood, and deletes
    the now unneeded picker session"""
    items = [
        {"id": "1", "mediaFile": {"filename": "a.jpg"}},
        {"id": "2", "mediaFile": {"filename": "b.jpg"}},
    ]
    deleted: list[str] = []
    _fake_picker_setup(monkeypatch, items, deleted)
    out_file = str(tmp_path / "out.csv")
    nb_photos = image_inventory.google_inventory(out_file, max_workers=2)
    assert nb_photos == 2
    assert deleted == ["s1"]
    with open(out_file, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == list(image_inventory.CSV_HEADER)
    full_paths = {row[0] for row in rows[1:]}
    assert full_paths == {"googlephotos:1", "googlephotos:2"}


def test_google_inventory_exits_when_nothing_was_picked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """google_inventory() exits instead of writing an empty, useless CSV when the user picked nothing"""
    _fake_picker_setup(monkeypatch, [], [])
    with pytest.raises(SystemExit):
        image_inventory.google_inventory(str(tmp_path / "out.csv"))


def test_google_inventory_extends_an_existing_csv_without_duplicating_photos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A 2nd run (eg because the picker limits a single selection) extends the CSV of a 1st run instead of replacing it,
    and a photo already in it (re-picked, or picked again by mistake) is neither re-fetched nor added a 2nd time"""
    out_file = str(tmp_path / "out.csv")
    item_1 = {"id": "1", "mediaFile": {"filename": "a.jpg", "baseUrl": "https://photos.example/1"}}
    item_2 = {"id": "2", "mediaFile": {"filename": "b.jpg", "baseUrl": "https://photos.example/2"}}
    _fake_picker_setup(monkeypatch, [item_1], [])
    assert image_inventory.google_inventory(out_file) == 1

    _fake_picker_setup(monkeypatch, [item_1, item_2], [])
    fetched_urls: list[str] = []
    monkeypatch.setattr(image_inventory.google_photos, "fetch_bytes", lambda _token, url, _params: fetched_urls.append(url) or None)
    nb_new = image_inventory.google_inventory(out_file)
    assert nb_new == 1  # Only "2" is new, "1" is skipped
    assert fetched_urls == ["https://photos.example/2"]  # "1" is not re-fetched

    with open(out_file, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    full_paths = [row[0] for row in rows[1:]]
    assert sorted(full_paths) == ["googlephotos:1", "googlephotos:2"]  # "1" is not duplicated


def test_google_inventory_returns_zero_when_every_picked_photo_is_already_inventoried(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-picking only photos already in the CSV does nothing (no fetch, no rewrite), rather than erroring out"""
    out_file = str(tmp_path / "out.csv")
    item = {"id": "1", "mediaFile": {"filename": "a.jpg", "baseUrl": "https://photos.example/1"}}
    _fake_picker_setup(monkeypatch, [item], [])
    image_inventory.google_inventory(out_file)

    _fake_picker_setup(monkeypatch, [item], [])
    monkeypatch.setattr(image_inventory.google_photos, "fetch_bytes", lambda *_a: pytest.fail("Should not re-fetch an already inventoried photo"))
    assert image_inventory.google_inventory(out_file) == 0


def test_main_google_defaults_the_output_to_the_pictures_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--google, without -o, writes to <Pictures>/google-photos-inventory.csv, and does not require -i"""
    monkeypatch.setattr(image_inventory, "_default_pictures_dir", lambda: str(tmp_path))
    called = {}
    monkeypatch.setattr(image_inventory, "google_inventory", lambda out_file, **_kwargs: called.setdefault("out_file", out_file) or 0)
    with patch.object(sys, "argv", ["imagetool", "inventory", "--google"]):
        tools.imagetool()
    assert called["out_file"] == str(tmp_path / image_inventory.DEFAULT_GOOGLE_OUTPUT)


def test_main_google_honors_the_output_option(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--google -o <file> writes to the given file instead of the Pictures directory default"""
    out_file = str(tmp_path / "custom.csv")
    called = {}
    monkeypatch.setattr(image_inventory, "google_inventory", lambda out, **_kwargs: called.setdefault("out_file", out) or 0)
    with patch.object(sys, "argv", ["imagetool", "inventory", "--google", "-o", out_file]):
        tools.imagetool()
    assert called["out_file"] == out_file


def test_chunks_splits_preserving_order() -> None:
    """The files are split into chunks of (almost) equal size, preserving their order"""
    files = [str(i) for i in range(10)]
    chunks = image_inventory._chunks(files, 3)
    assert [f for chunk in chunks for f in chunk] == files
    assert len(chunks) <= 3


def test_process_chunk_reports_progress_after_each_photo(monkeypatch: pytest.MonkeyPatch) -> None:
    """progress_done() is called right after each photo is processed, not only once the whole chunk is done, so the progress
    is reported as the photos are actually processed instead of in one burst at the end of the chunk"""
    order = []

    class FakeHelper:
        """A fake ExifToolHelper usable as a context manager"""

        def __enter__(self) -> None:
            return None

        def __exit__(self, *_args: object) -> bool:
            return False

    monkeypatch.setattr(image_inventory, "photo_row", lambda _et, f: order.append(f"row:{f}") or [f])
    monkeypatch.setattr(image_inventory, "ExifToolHelper", lambda **_kwargs: FakeHelper())
    rows = image_inventory._process_chunk(["a", "b", "c"], lambda: order.append("done"))
    assert order == ["row:a", "done", "row:b", "done", "row:c", "done"]
    assert rows == [["a"], ["b"], ["c"]]


def test_progress_logs_every_period_and_on_completion_with_eta(monkeypatch: pytest.MonkeyPatch) -> None:
    """The progress and its ETA are logged once the period has elapsed, and always for the last photo, even if the period
    has not elapsed; the ETA is the time to process the remaining photos at the average speed observed so far"""
    times = iter([0, 10, 35, 36])  # 0: _progress_logger() start, then one value per done() call
    monkeypatch.setattr(image_inventory.time, "monotonic", lambda: next(times))
    with mock.patch.object(image_inventory.log.logger, "info") as log_info:
        done = image_inventory._progress_logger(3)
        done()  # elapsed since start = 10, not logged (period is 30s)
        done()  # elapsed since start = 35, logged: 1 photo remaining at 35/2 s/photo = ETA 17.5s
        done()  # elapsed since last log = 1s, but last photo, logged regardless
    assert log_info.call_count == 2
    assert log_info.call_args_list[0].args[1:] == (2, 3, "00:00:17.500")
    assert log_info.call_args_list[1].args[1:] == (3, 3, "00:00:00.000")


def test_collect_photos_keeps_files_and_expands_directories(tmp_path: Path) -> None:
    """Files given directly are kept whatever their extension, directories are walked recursively for image files only"""
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "photo.jpg").write_bytes(b"0")
    (tmp_path / "sub" / "notes.txt").write_bytes(b"0")
    given_file = tmp_path / "given.txt"
    given_file.write_bytes(b"0")
    files = image_inventory._collect_photos([str(given_file), str(tmp_path / "sub")])
    assert set(files) == {str(given_file), str(tmp_path / "sub" / "photo.jpg")}


def test_collect_photos_excludes_gif_files(tmp_path: Path) -> None:
    """GIF files are never inventoried, whether found under a scanned directory or given directly in -i"""
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "photo.jpg").write_bytes(b"0")
    (tmp_path / "sub" / "animation.gif").write_bytes(b"0")
    given_gif = tmp_path / "given.gif"
    given_gif.write_bytes(b"0")
    files = image_inventory._collect_photos([str(given_gif), str(tmp_path / "sub")])
    assert set(files) == {str(tmp_path / "sub" / "photo.jpg")}


def test_collect_photos_excludes_the_recycle_bin(tmp_path: Path) -> None:
    """The Windows recycle bin is never walked into when scanning a directory or disk drive"""
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "photo.jpg").write_bytes(b"0")
    recycle_bin = tmp_path / "$RECYCLE.BIN" / "S-1-5-21"
    recycle_bin.mkdir(parents=True)
    (recycle_bin / "deleted-photo.jpg").write_bytes(b"0")
    files = image_inventory._collect_photos([str(tmp_path)])
    assert set(files) == {str(tmp_path / "sub" / "photo.jpg")}


def test_collect_photos_exits_when_nothing_is_found(tmp_path: Path) -> None:
    """Exits with code 1 when no photo is found in the given paths"""
    with pytest.raises(SystemExit) as exc:
        image_inventory._collect_photos([str(tmp_path)])
    assert exc.value.code == 1


def test_collect_photos_logs_a_final_message_once_complete(tmp_path: Path) -> None:
    """Once the collection is complete, a distinct final message announces the total count and the next step"""
    (tmp_path / "photo.jpg").write_bytes(b"0")
    with mock.patch.object(image_inventory.log.logger, "info") as log_info:
        files = image_inventory._collect_photos([str(tmp_path)])
    assert len(files) == 1
    assert log_info.call_args_list[-1].args == ("%d images collected, now processing...", 1)


def test_collect_photos_logs_progress_every_period(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The number of photos collected so far is logged every COLLECT_PROGRESS_PERIOD seconds while walking the directories"""
    names = [f"photo{i}.jpg" for i in range(3)]
    monkeypatch.setattr(image_inventory.os, "walk", lambda _path: [("root", [], names)])
    monkeypatch.setattr(image_inventory.fil, "is_image_file", lambda _name: True)
    times = iter([0, 4, 11, 12])  # 0: start, then one value per file collected
    monkeypatch.setattr(image_inventory.time, "monotonic", lambda: next(times))
    with mock.patch.object(image_inventory.log.logger, "info") as log_info:
        files = image_inventory._collect_photos([str(tmp_path)])
    assert len(files) == 3
    assert log_info.call_count == 2  # Once at 11s (>= 10s period), once at the end
    assert log_info.call_args_list[0].args[1] == 2
    assert log_info.call_args_list[-1].args[1] == 3


def test_load_reusable_rows_returns_empty_when_the_csv_doesnt_exist_yet(tmp_path: Path) -> None:
    """Without an existing CSV at out_file, there is nothing to reuse: every photo is (re)computed"""
    assert image_inventory._load_reusable_rows(str(tmp_path / "missing.csv")) == ({}, None)


def test_load_reusable_rows_reads_existing_rows_keyed_by_full_path(tmp_path: Path) -> None:
    """An existing CSV's rows are indexed by their full_path, for _reusable_row() to look up by file"""
    out_file = tmp_path / "inventory.csv"
    with open(out_file, "w", newline="", encoding="utf-8") as fh:
        csv_writer = csv.writer(fh)
        csv_writer.writerow(image_inventory.PHOTO_CSV_HEADER)
        csv_writer.writerow(_row(full_path="a.jpg", file_name="a.jpg", fingerprint="00000000"))
    reusable, csv_mtime = image_inventory._load_reusable_rows(str(out_file))
    assert set(reusable) == {"a.jpg"}
    assert csv_mtime == out_file.stat().st_mtime


def test_reusable_row_reuses_a_photo_unchanged_since_the_csv(tmp_path: Path) -> None:
    """A photo not modified since the existing CSV was written reuses its row, unchanged"""
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"0")
    row = ["anything"]
    future_mtime = photo.stat().st_mtime + 10
    assert image_inventory._reusable_row(str(photo), {os.path.abspath(str(photo)): row}, future_mtime) is row


def test_reusable_row_returns_none_when_the_photo_was_modified_after_the_csv(tmp_path: Path) -> None:
    """A photo modified after the existing CSV was written must be recomputed, not reused"""
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"0")
    past_mtime = photo.stat().st_mtime - 10
    assert image_inventory._reusable_row(str(photo), {os.path.abspath(str(photo)): ["anything"]}, past_mtime) is None


def test_reusable_row_returns_none_when_there_is_nothing_to_reuse(tmp_path: Path) -> None:
    """A new photo, or no existing CSV at all, is always (re)computed"""
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"0")
    assert image_inventory._reusable_row(str(photo), {}, time.time() + 10) is None  # Not in the existing CSV
    assert image_inventory._reusable_row(str(photo), {os.path.abspath(str(photo)): ["anything"]}, None) is None  # No existing CSV


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
    assert values["fingerprint"] == image_inventory.compute_fingerprint(REAL_IMAGE)


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


def test_inventory_reuses_an_unchanged_photo_without_recomputing_its_fingerprint(tmp_path: Path) -> None:
    """Re-running inventory() over the same photo, with the same out_file, reuses its row from the existing CSV
    instead of recomputing its fingerprint and metadata, since the photo has not changed since"""
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(Path(REAL_IMAGE).read_bytes())
    out_file = str(tmp_path / "inventory.csv")
    image_inventory.inventory([str(photo)], out_file, max_workers=2)

    with mock.patch.object(image_inventory, "photo_row", wraps=image_inventory.photo_row) as spy:
        nb_photos = image_inventory.inventory([str(photo)], out_file, max_workers=2)
    assert nb_photos == 1
    spy.assert_not_called()
    with open(out_file, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert dict(zip(image_inventory.CSV_HEADER, rows[1], strict=True))["fingerprint"] == image_inventory.compute_fingerprint(REAL_IMAGE)


def test_inventory_recomputes_a_photo_modified_after_the_csv(tmp_path: Path) -> None:
    """A photo modified after the existing CSV was written is recomputed, not reused, even though it was already in it"""
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(Path(REAL_IMAGE).read_bytes())
    out_file = str(tmp_path / "inventory.csv")
    image_inventory.inventory([str(photo)], out_file, max_workers=2)

    future = time.time() + 10
    os.utime(photo, (future, future))
    with mock.patch.object(image_inventory, "photo_row", wraps=image_inventory.photo_row) as spy:
        image_inventory.inventory([str(photo)], out_file, max_workers=2)
    spy.assert_called_once()


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
