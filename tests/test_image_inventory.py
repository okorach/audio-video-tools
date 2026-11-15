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
import types
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
