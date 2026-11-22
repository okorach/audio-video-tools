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

"""Tool that inventories the photos found in directories and/or disk drives, or picked from a Google Photos library
(--google), into a CSV file: full path, short name, size, dimensions, a perceptual fingerprint, dates (taken, created,
modified), GPS coordinates, device and other common EXIF metadata, and a duplicate likelihood (how much a photo looks
like another one of the inventory, based on its fingerprint and its metadata) to help detect duplicates and
near-duplicates. --dedup interactively reviews these likely duplicates, from an existing inventory CSV, and deletes
one of each pair"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import io
import itertools
import os
import re
import sys
import threading
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING

from exiftool import ExifToolHelper
from PIL import Image, ImageOps

import mediatools.utilities as util
import utilities.file as fil
from mediatools import google_photos, log, media_config

if TYPE_CHECKING:
    from collections.abc import Callable

COLLECT_PROGRESS_PERIOD: int = 10  # Seconds between 2 progress log lines while collecting the photos to inventory
PROGRESS_PERIOD: int = 30  # Seconds between 2 progress log lines while processing the photos
DEFAULT_WORKERS: int = 8
DEFAULT_OUTPUT: str = "photo-inventory.csv"
DATE_FMT: str = "%Y-%m-%d %H:%M:%S"
FINGERPRINT_GRID: int = 16  # Side of the grayscale thumbnail the fingerprint is computed from: 256 bits long

# Columns computed for each photo on its own, before any other photo is known
PHOTO_CSV_HEADER: tuple[str, ...] = (
    "full_path",
    "file_name",
    "size_bytes",
    "width",
    "height",
    "fingerprint",
    "date_taken",
    "date_created",
    "date_modified",
    "gps_latitude",
    "gps_longitude",
    "gps_altitude",
    "device",
    "lens_model",
    "iso",
    "aperture",
    "exposure_time",
    "focal_length",
    "orientation",
    "software",
)
# Columns computed last, by comparing every photo to the others, see add_duplicate_likelihood()
DUPLICATE_CSV_HEADER: tuple[str, ...] = ("duplicate_likelihood", "duplicate_of")
CSV_HEADER: tuple[str, ...] = PHOTO_CSV_HEADER + DUPLICATE_CSV_HEADER

WIDTH_HEIGHT_TAGS: tuple[tuple[str, str], ...] = (
    ("File:ImageWidth", "File:ImageHeight"),
    ("EXIF:ExifImageWidth", "EXIF:ExifImageHeight"),
)
DATE_TAKEN_TAGS: tuple[str, ...] = ("EXIF:DateTimeOriginal", "EXIF:CreateDate")


def _progress_logger(total: int) -> Callable[[], None]:
    """Returns a thread-safe function that records one more photo processed out of total, and logs the progress and the ETA
    (estimated from the average time per photo processed so far, applied to the remaining photos) at most once every
    PROGRESS_PERIOD seconds, and always for the last photo"""
    lock = threading.Lock()
    start = time.monotonic()
    state = {"count": 0, "last_log": start}

    def done() -> None:
        """Records that a photo has been inventoried, and logs the progress and the ETA if due"""
        with lock:
            state["count"] += 1
            now = time.monotonic()
            if now - state["last_log"] >= PROGRESS_PERIOD or state["count"] >= total:
                eta = (total - state["count"]) * (now - start) / state["count"]
                log.logger.info("Processed %d/%d images - ETA %s", state["count"], total, util.to_hms_str(eta))
                state["last_log"] = now

    return done


EXCLUDED_EXTENSIONS: tuple[str, ...] = ("gif",)  # Not photos: animations, screenshots... never inventoried, even if given directly
EXCLUDED_DIRS: tuple[str, ...] = ("$recycle.bin",)  # The Windows recycle bin: never walked into when scanning a directory/drive


def _is_excluded(filename: str) -> bool:
    """Returns whether filename has one of the EXCLUDED_EXTENSIONS, always skipped by the inventory"""
    return filename.lower().rsplit(".", 1)[-1] in EXCLUDED_EXTENSIONS


def _is_excluded_dir(dirname: str) -> bool:
    """Returns whether dirname (a directory name, not a path) is one of EXCLUDED_DIRS, never walked into"""
    return dirname.lower() in EXCLUDED_DIRS


def _collect_photos(paths: list[str]) -> list[str]:
    """Expands the files, directories and/or disk drives given in paths into the list of photos they contain (directories are
    walked recursively, except into EXCLUDED_DIRS, and files are kept as given whatever their extension, except
    EXCLUDED_EXTENSIONS which are always skipped). Logs the number of photos collected so far every COLLECT_PROGRESS_PERIOD
    seconds, since walking a whole disk drive can take a while before the inventory itself starts. Exits with code 1 if no
    photo is found"""
    files: list[str] = []
    last_log = time.monotonic()
    for path in paths:
        if not os.path.isdir(path):
            if not _is_excluded(path):
                files.append(path)
            continue
        for root, dirs, names in os.walk(path):
            dirs[:] = [d for d in dirs if not _is_excluded_dir(d)]
            for name in names:
                if not fil.is_image_file(name) or _is_excluded(name):
                    continue
                files.append(os.path.join(root, name))
                now = time.monotonic()
                if now - last_log >= COLLECT_PROGRESS_PERIOD:
                    log.logger.info("Collected %d images for inventory", len(files))
                    last_log = now
    if not files:
        log.logger.error("No input file found in %s", ", ".join(paths))
        sys.exit(1)
    log.logger.info("%d images collected, now processing...", len(files))
    return files


def _get_dimensions(exif_data: dict) -> tuple[int | None, int | None]:
    """Returns the (width, height) of a photo from its EXIF data, trying the most common tags in turn,
    (None, None) if none of them is present"""
    for w_tag, h_tag in WIDTH_HEIGHT_TAGS:
        if w_tag in exif_data and h_tag in exif_data:
            return int(exif_data[w_tag]), int(exif_data[h_tag])
    size = exif_data.get("Composite:ImageSize")
    if size:
        w, h = str(size).replace("x", " ").split()[:2]
        return int(float(w)), int(float(h))
    return None, None


def _get_gps(exif_data: dict) -> tuple[float | None, float | None, float | None]:
    """Returns the (latitude, longitude, altitude) of a photo from its EXIF data, None values when missing"""
    try:
        lat, lon = float(exif_data["Composite:GPSLatitude"]), float(exif_data["Composite:GPSLongitude"])
    except (KeyError, TypeError, ValueError):
        return None, None, None
    alt = exif_data.get("Composite:GPSAltitude")
    return lat, lon, float(alt) if isinstance(alt, (int, float)) else None


def _get_device(exif_data: dict) -> str | None:
    """Returns the device (make and model) that took a photo, from its EXIF data, None if there is none"""
    make = str(exif_data.get("EXIF:Make", "")).strip()
    model = str(exif_data.get("EXIF:Model", "")).strip()
    return f"{make} {model}".strip() or None


def _get_date_taken(exif_data: dict) -> datetime | None:
    """Returns the date a photo was taken, from its EXIF data (DateTimeOriginal, else CreateDate), None if there is none"""
    for tag in DATE_TAKEN_TAGS:
        value = str(exif_data.get(tag) or "")
        if value and value[0:4].isdigit() and int(value[0:4]) > 1970:
            try:
                return datetime.strptime(value, util.EXIF_DATE_FMT)
            except ValueError:
                continue
    return None


def _fingerprint_from_image(img: Image.Image, context: str) -> str | None:
    """Returns the perceptual fingerprint (see compute_fingerprint()) of an already opened Pillow image, a difference
    hash of a small grayscale thumbnail of it (after applying its EXIF orientation). context only names the photo in
    the warning logged if its pixels can't be processed, None in that case"""
    try:
        nb_pixels = img.width * img.height
        if Image.MAX_IMAGE_PIXELS and nb_pixels > Image.MAX_IMAGE_PIXELS:
            # Pillow itself only warns about this (without naming the file), decoding such a large image may be slow
            log.logger.warning("%s is a very large image (%d pixels), its fingerprint may take a while to compute", context, nb_pixels)
        resample = getattr(Image, "Resampling", Image).LANCZOS
        thumbnail = ImageOps.exif_transpose(img).convert("L").resize((FINGERPRINT_GRID + 1, FINGERPRINT_GRID), resample)
        pixels = list(getattr(thumbnail, "get_flattened_data", thumbnail.getdata)())
    except Exception as e:
        log.logger.warning("Could not compute the fingerprint of %s: %s", context, e)
        return None
    width = FINGERPRINT_GRID + 1
    bits = "".join(
        "1" if pixels[row * width + col] > pixels[row * width + col + 1] else "0"
        for row in range(FINGERPRINT_GRID)
        for col in range(FINGERPRINT_GRID)
    )
    return f"{int(bits, 2):0{len(bits) // 4}x}"


def compute_fingerprint(filename: str) -> str | None:
    """Returns a perceptual fingerprint of a photo, as a hex string, computed only from its pixels (not from its file name
    or its metadata): a difference hash of a small grayscale thumbnail of the photo (after applying its EXIF orientation),
    so that it is identical for the exact same image, and close (small hamming_distance()) for the same image resized or
    cropped a bit, which can later be used to compute a match probability between two photos. None if the photo can't be
    read as an image"""
    try:
        with Image.open(filename) as img:
            return _fingerprint_from_image(img, filename)
    except Exception as e:
        log.logger.warning("Could not compute the fingerprint of %s: %s", filename, e)
        return None


def compute_fingerprint_from_bytes(data: bytes, context: str) -> str | None:
    """Same as compute_fingerprint(), but from image bytes already in memory (eg downloaded from a Google Photos
    thumbnail URL) instead of a local file; context names the photo in the warning logged if anything goes wrong"""
    try:
        with Image.open(io.BytesIO(data)) as img:
            return _fingerprint_from_image(img, context)
    except Exception as e:
        log.logger.warning("Could not compute the fingerprint of %s: %s", context, e)
        return None


def hamming_distance(fingerprint_1: str | None, fingerprint_2: str | None) -> int | None:
    """Returns the number of bits that differ between two fingerprints returned by compute_fingerprint(), a measure of how
    close two photos are (0 for identical fingerprints), None if either fingerprint is None or they are not the same length"""
    if fingerprint_1 is None or fingerprint_2 is None or len(fingerprint_1) != len(fingerprint_2):
        return None
    return (int(fingerprint_1, 16) ^ int(fingerprint_2, 16)).bit_count()


FP_MAX_DISTANCE: int = 40  # Hamming distance (out of 256 bits) at or above which 2 fingerprints are considered unrelated
FP_BUCKET_CHARS: int = 4  # Leading hex characters (16 bits) of the fingerprint shared by 2 photos to consider them duplicate candidates
GPS_MAX_DISTANCE_DEGREES: float = 0.0005  # ~ 50m, close enough to consider 2 GPS coordinates the same place
MIN_APPLICABLE_WEIGHT: float = 0.3  # Minimum total weight of the applicable criteria to compute a duplicate likelihood at all
# How much each criterion weighs in the duplicate likelihood, when applicable (ie present on both photos compared)
SIMILARITY_WEIGHTS: dict[str, float] = {
    "fingerprint": 0.5,
    "size_bytes": 0.15,
    "dimensions": 0.1,
    "date_taken": 0.15,
    "device": 0.05,
    "gps": 0.05,
}


def _row_value(row: list[object], column: str) -> object:
    """Returns the value of column in row (a row of PHOTO_CSV_HEADER columns), None if it is empty"""
    value = row[PHOTO_CSV_HEADER.index(column)]
    return value if value not in ("", None) else None


def _dimensions_match(row_a: list[object], row_b: list[object]) -> float | None:
    """Returns 1.0/0.0 for matching/differing (width, height), None if either photo is missing one of them"""
    size_a = (_row_value(row_a, "width"), _row_value(row_a, "height"))
    size_b = (_row_value(row_b, "width"), _row_value(row_b, "height"))
    if None in size_a or None in size_b:
        return None
    return float((str(size_a[0]), str(size_a[1])) == (str(size_b[0]), str(size_b[1])))


def _gps_match(row_a: list[object], row_b: list[object]) -> float | None:
    """Returns 1.0/0.0 for GPS coordinates within GPS_MAX_DISTANCE_DEGREES of each other, None if either is missing"""
    coords_a = (_row_value(row_a, "gps_latitude"), _row_value(row_a, "gps_longitude"))
    coords_b = (_row_value(row_b, "gps_latitude"), _row_value(row_b, "gps_longitude"))
    if None in coords_a or None in coords_b:
        return None
    return float(all(abs(float(a) - float(b)) <= GPS_MAX_DISTANCE_DEGREES for a, b in zip(coords_a, coords_b, strict=True)))


def _exact_match(column: str) -> Callable[[list[object], list[object]], float | None]:
    """Returns a function comparing the column of 2 rows for an exact match, None if either row is missing it"""

    def compare(row_a: list[object], row_b: list[object]) -> float | None:
        """Returns 1.0/0.0 for a matching/differing column, None if either row is missing it"""
        value_a, value_b = _row_value(row_a, column), _row_value(row_b, column)
        return None if value_a is None or value_b is None else float(str(value_a) == str(value_b))

    return compare


def _fingerprint_match(row_a: list[object], row_b: list[object]) -> float | None:
    """Returns the fingerprint similarity (1.0 for identical, decreasing to 0.0 at FP_MAX_DISTANCE), None if either
    photo has no fingerprint"""
    distance = hamming_distance(_row_value(row_a, "fingerprint"), _row_value(row_b, "fingerprint"))
    return None if distance is None else max(0.0, 1 - distance / FP_MAX_DISTANCE)


# One match function per criterion of SIMILARITY_WEIGHTS, each returning 1.0/0.0 (or a similarity in between for the
# fingerprint), None when the criterion is not applicable (missing on either photo)
_MATCH_FUNCTIONS: dict[str, Callable[[list[object], list[object]], float | None]] = {
    "fingerprint": _fingerprint_match,
    "size_bytes": _exact_match("size_bytes"),
    "dimensions": _dimensions_match,
    "date_taken": _exact_match("date_taken"),
    "device": _exact_match("device"),
    "gps": _gps_match,
}


def _similarity(row_a: list[object], row_b: list[object]) -> int | None:
    """Returns the duplicate likelihood (0-100) between 2 photo rows: a weighted average (SIMILARITY_WEIGHTS) of how
    close their fingerprint is and how many of their other metadata match, computed only over the criteria applicable
    to both photos (missing metadata does not count against the likelihood, it is just ignored). None if too few
    criteria are applicable to say anything meaningful"""
    applicable_weight = 0.0
    matched_weight = 0.0
    for key, weight in SIMILARITY_WEIGHTS.items():
        match = _MATCH_FUNCTIONS[key](row_a, row_b)
        if match is not None:
            applicable_weight += weight
            matched_weight += weight * match
    if applicable_weight < MIN_APPLICABLE_WEIGHT:
        return None
    return round(100 * matched_weight / applicable_weight)


def _duplicate_candidates(rows: list[list[object]]) -> set[tuple[int, int]]:
    """Returns the (i, j) index pairs (i < j) of rows worth comparing in detail with _similarity(), because they share an
    exact size, an exact date taken, or the first FP_BUCKET_CHARS of their fingerprint. Comparing every photo to every
    other one does not scale to a large inventory, so only the photos sharing one of these cheap-to-index, exact criteria
    are considered duplicate candidates"""
    buckets: dict[tuple[str, object], list[int]] = {}
    for i, row in enumerate(rows):
        size, date_taken, fingerprint = _row_value(row, "size_bytes"), _row_value(row, "date_taken"), _row_value(row, "fingerprint")
        if size is not None:
            buckets.setdefault(("size", size), []).append(i)
        if date_taken is not None:
            buckets.setdefault(("date", date_taken), []).append(i)
        if fingerprint is not None:
            buckets.setdefault(("fp", fingerprint[:FP_BUCKET_CHARS]), []).append(i)
    pairs: set[tuple[int, int]] = set()
    for indices in buckets.values():
        for i, j in itertools.combinations(indices, 2):
            pairs.add((i, j) if i < j else (j, i))
    return pairs


def add_duplicate_likelihood(rows: list[list[object]]) -> None:
    """Appends, to each row of PHOTO_CSV_HEADER columns, its duplicate likelihood (0-100, empty if none found) with the
    most likely duplicate among the other rows, and the full path of that most likely duplicate (empty if none), turning
    each row into a row of CSV_HEADER columns. See _similarity() for how the likelihood is computed, and
    _duplicate_candidates() for which pairs of rows are actually compared with each other"""
    full_path_idx = PHOTO_CSV_HEADER.index("full_path")
    best_score = [0] * len(rows)
    best_match: list[object] = [None] * len(rows)
    for i, j in _duplicate_candidates(rows):
        score = _similarity(rows[i], rows[j])
        if score is None:
            continue
        if score > best_score[i]:
            best_score[i], best_match[i] = score, rows[j][full_path_idx]
        if score > best_score[j]:
            best_score[j], best_match[j] = score, rows[i][full_path_idx]
    for row, score, match in zip(rows, best_score, best_match, strict=True):
        row.append(score or "")
        row.append(match or "")


def _write_csv(rows: list[list[object]], out_file: str) -> None:
    """Writes rows (of CSV_HEADER columns) to out_file, with the CSV header as the first line"""
    with open(out_file, "w", newline="", encoding="utf-8") as fh:
        csv_writer = csv.writer(fh, dialect="excel", quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(CSV_HEADER)
        csv_writer.writerows(rows)


_CSV_FLOAT_COLUMNS: tuple[str, ...] = ("gps_latitude", "gps_longitude", "gps_altitude")


def _read_inventory_csv(csv_file: str) -> list[list[object]]:
    """Reads an existing photo inventory CSV (as written by inventory() or this function's caller, with or without the
    duplicate_likelihood and duplicate_of columns) and returns its rows as rows of PHOTO_CSV_HEADER columns, ready for
    add_duplicate_likelihood() to amend, without rescanning the photos themselves"""
    rows = []
    with open(csv_file, newline="", encoding="utf-8") as fh:
        for record in csv.DictReader(fh):
            row = [record.get(column) or None for column in PHOTO_CSV_HEADER]
            for column in _CSV_FLOAT_COLUMNS:
                value = row[PHOTO_CSV_HEADER.index(column)]
                if value is not None:
                    row[PHOTO_CSV_HEADER.index(column)] = float(value)
            rows.append(row)
    return rows


DEDUP_SIZE_RATIO_THRESHOLD: float = 0.8  # A photo is "significantly smaller" than the other one if below this ratio of its size


def _to_float(value: str | None) -> float | None:
    """Returns value as a float, None if it is empty or missing"""
    return float(value) if value else None


def _regex_priority_rule(pattern: re.Pattern) -> Callable[[dict[str, str], dict[str, str]], int | None]:
    """Returns a dedup rule recommending the deletion of whichever of 2 photos' full_path matches pattern, when only
    one of the two does, None if both or neither do. Used to turn every configurable pattern group below (see
    _configured_patterns()) into a dedup rule: a photo matching one of a group's patterns, while the other doesn't,
    is the candidate for deletion"""

    def rule(row_a: dict[str, str], row_b: dict[str, str]) -> int | None:
        """Returns 1 or 2, the photo whose full_path matches pattern, None if both or neither do"""
        in_a, in_b = bool(pattern.search(row_a["full_path"])), bool(pattern.search(row_b["full_path"]))
        if in_a and not in_b:
            return 1
        if in_b and not in_a:
            return 2
        return None

    return rule


def _configured_patterns(property_name: str, defaults: tuple[re.Pattern, ...]) -> tuple[re.Pattern, ...]:
    """Returns the compiled, case-insensitive regexes configured for property_name, read fresh from the
    configuration every time (a semicolon-separated list, matched against a candidate duplicate's full_path, in
    priority order; surrounding whitespace around each regex is stripped and ignored, so it has no effect), so a
    user can extend or replace the pattern-based dedup criteria from ~/.mediatools.properties without code changes.
    Falls back to defaults when the property is missing or empty (eg an existing ~/.mediatools.properties created
    before that property existed)"""
    value = media_config.get_property(property_name)
    if not value:
        return defaults
    return tuple(re.compile(pattern.strip(), re.IGNORECASE) for pattern in str(value).split(";") if pattern.strip())


# A ".picasaoriginals" folder holds Picasa's hidden backup of a photo's pixels before any edit done in the app
_PICASA_ORIGINALS_PATTERN: str = r"[\\/]\.picasaoriginals[\\/]"
# A tilde anywhere in the full path, as commonly found in a backup or temporary copy's name (eg "~lockfile",
# "image~.jpg")
_TILDE_PATTERN: str = r"~"
# A "copy"/"copie" suffix on the file name (before its extension), as commonly added when a file is duplicated by a
# file manager (eg "some-picture copie.jpg", "some-picture - Copy.jpg", "some-picture copy (2).jpg")
_COPY_SUFFIX_PATTERN: str = r"[ _-](copy|copie)(\s*\(\d+\))?\.[^.\\/]+$"
# A folder (not the file name itself, hence the trailing separator) whose name contains "duplicate", as commonly
# used for folders already known to hold duplicate photos (eg "Duplicates", "Duplicate Photos", "zzz_duplicates")
_DUPLICATE_FOLDER_PATTERN: str = r"(?:^|[\\/])[^\\/]*duplicate[^\\/]*[\\/]"
# A folder (not the file name itself) named "a_trier"/"a trier" (French for "to be sorted"), whatever its case,
# accent or underscore/space spelling
_TO_SORT_FOLDER_PATTERN: str = r"(?:^|[\\/])[aà][ _]trier[\\/]"
# Unedited camera/phone original file names, as opposed to a descriptive name a photo was renamed to: eg IMG_1234.jpg,
# IMG_20180209_082726_HDR.jpg (Android), IMG-20200101-WA0001.jpg (WhatsApp), PXL_20210101_123456.jpg (Pixel),
# PANO_20190415_103823.jpg (Android panorama), DSC_0001.jpg, HPIM1234.jpg (HP cameras), 100_1234.jpg
# (point-and-shoot cameras), 20130804_174038.jpg (date_time, no camera prefix), "25-12-2011 16-46-10_0021.JPG"
# (DD-MM-YYYY HH-MM-SS_sequence, used by some photo management software), "2014-07-20 20.19.20.jpg"
# (YYYY-MM-DD HH.MM.SS, used by other photo management software)
_ORIGINAL_FILENAME_PATTERNS: tuple[str, ...] = (
    r"(?:^|[\\/])img[-_]?\d[\d_]*(_hdr)?\.[^.\\/]+$",
    r"(?:^|[\\/])img-\d{8}-wa\d+\.[^.\\/]+$",
    r"(?:^|[\\/])dsc[fn]?[-_]?\d[\d_]*\.[^.\\/]+$",
    r"(?:^|[\\/])hpim\d+\.[^.\\/]+$",
    r"(?:^|[\\/])pxl[-_]?\d[\d_]*\.[^.\\/]+$",
    r"(?:^|[\\/])pano[-_]?\d{8}[-_]\d{6}\.[^.\\/]+$",
    r"(?:^|[\\/])vid[-_]?\d[\d_]*\.[^.\\/]+$",
    r"(?:^|[\\/])mov[-_]?\d[\d_]*\.[^.\\/]+$",
    r"(?:^|[\\/])mvimg[-_]?\d[\d_]*\.[^.\\/]+$",
    r"(?:^|[\\/])p\d{7,}\.[^.\\/]+$",
    r"(?:^|[\\/])gopr\d{3,}\.[^.\\/]+$",
    r"(?:^|[\\/])\d{3,4}[-_]\d{3,}\.[^.\\/]+$",
    r"(?:^|[\\/])\d{8}[-_]\d{6}\.[^.\\/]+$",
    r"(?:^|[\\/])signal-\d{4}-\d{2}-\d{2}-\d{6}(-\d+)?\.[^.\\/]+$",
    r"(?:^|[\\/])wa\d{10,}\.[^.\\/]+$",
    r"(?:^|[\\/])\d{2}-\d{2}-\d{4} \d{2}-\d{2}-\d{2}_\d+\.[^.\\/]+$",
    r"(?:^|[\\/])\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2}\.[^.\\/]+$",
)

DELETE_PRIORITY_PROPERTY: str = "dedup.delete_priority"
# Patterns checked first, before the sequence-number, size and GPS rules: a photo matching one of these, while the
# other doesn't, is the candidate for deletion. Checked in this order (low-quality/backup copy, duplicate folder,
# to-sort folder, then original camera/phone file name); default used when DELETE_PRIORITY_PROPERTY is missing
DEFAULT_DELETE_PRIORITY_PATTERNS: tuple[re.Pattern, ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        _PICASA_ORIGINALS_PATTERN,
        _TILDE_PATTERN,
        _COPY_SUFFIX_PATTERN,
        _DUPLICATE_FOLDER_PATTERN,
        _TO_SORT_FOLDER_PATTERN,
        *_ORIGINAL_FILENAME_PATTERNS,
    )
)


def _delete_priority_patterns() -> tuple[re.Pattern, ...]:
    """Returns the delete-priority patterns (see DEFAULT_DELETE_PRIORITY_PATTERNS, DELETE_PRIORITY_PROPERTY and
    _configured_patterns())"""
    return _configured_patterns(DELETE_PRIORITY_PROPERTY, DEFAULT_DELETE_PRIORITY_PATTERNS)


def _size_rule(row_a: dict[str, str], row_b: dict[str, str]) -> int | None:
    """Returns 1 or 2, the photo significantly smaller (DEDUP_SIZE_RATIO_THRESHOLD) than the other one, None if neither
    is, or either size is missing"""
    size_a, size_b = _to_float(row_a.get("size_bytes")), _to_float(row_b.get("size_bytes"))
    if not size_a or not size_b:
        return None
    if size_a < size_b * DEDUP_SIZE_RATIO_THRESHOLD:
        return 1
    if size_b < size_a * DEDUP_SIZE_RATIO_THRESHOLD:
        return 2
    return None


def _gps_rule(row_a: dict[str, str], row_b: dict[str, str]) -> int | None:
    """Returns 1 or 2, the photo missing GPS coordinates while the other one has them, None if both or neither have them"""
    gps_a, gps_b = _to_float(row_a.get("gps_latitude")), _to_float(row_b.get("gps_latitude"))
    if gps_a is not None and gps_b is None:
        return 2
    if gps_b is not None and gps_a is None:
        return 1
    return None


# A file name's trailing sequence number (eg "081" in "Vallandry 2016 081.jpg"), captured along with everything before
# it (its "prefix", eg "Vallandry 2016 "), so 2 file names can be compared for sharing the same prefix
_SEQUENCE_SUFFIX_PATTERN: re.Pattern = re.compile(r"^(?P<prefix>.*\D)(?P<seq>\d+)$")


def _sequence_number(file_name: str) -> tuple[str, int] | None:
    """Returns (prefix, sequence number) of file_name's trailing sequence number (eg ("Vallandry 2016 ", 81) for
    "Vallandry 2016 081.jpg"), None if its name (without extension) doesn't end in one"""
    match = _SEQUENCE_SUFFIX_PATTERN.match(os.path.splitext(file_name)[0])
    return (match["prefix"], int(match["seq"])) if match else None


def _sequence_number_rule(row_a: dict[str, str], row_b: dict[str, str]) -> int | None:
    """Returns 1 or 2, the photo with the highest trailing sequence number, when both photos sit in the exact same
    folder and their file names only differ by that number (eg "Vallandry 2016 081.jpg" and "Vallandry 2016
    140.jpg"): such a pair is the same shot exported/copied twice under the same batch-numbering scheme, once under
    its own sequence number and once under a later one, so the one with the highest number (the later copy) is
    recommended. None if either photo is not a local file, they are not in the same folder, their file names don't
    share such a prefix, or the sequence numbers are equal. Not pattern-based (it compares the 2 photos' numbers to
    each other), so it is not configurable like the rules above"""
    if not _is_local_path(row_a["full_path"]) or not _is_local_path(row_b["full_path"]):
        return None
    if os.path.dirname(row_a["full_path"]) != os.path.dirname(row_b["full_path"]):
        return None
    seq_a, seq_b = _sequence_number(row_a["file_name"]), _sequence_number(row_b["file_name"])
    if not seq_a or not seq_b or seq_a[0] != seq_b[0] or seq_a[1] == seq_b[1]:
        return None
    return 1 if seq_a[1] > seq_b[1] else 2


def _recommend_deletion(row_a: dict[str, str], row_b: dict[str, str]) -> int | None:
    """Returns 1 or 2, the photo of the pair (row_a, row_b) recommended for deletion, by the first conclusive rule,
    in this order: the delete-priority patterns (configurable, see _configured_patterns()), then the
    sequence-number, size and GPS rules (not pattern-based, not configurable). None if none of them is conclusive"""
    rules: tuple[Callable[[dict[str, str], dict[str, str]], int | None], ...] = (
        *(_regex_priority_rule(pattern) for pattern in _delete_priority_patterns()),
        _sequence_number_rule,
        _size_rule,
        _gps_rule,
    )
    for rule in rules:
        recommendation = rule(row_a, row_b)
        if recommendation is not None:
            return recommendation
    return None


def _format_size(size_bytes: str | None) -> str:
    """Returns a human readable file size (eg '3.2 MB'), 'N/A' if size_bytes is empty"""
    size = _to_float(size_bytes)
    if size is None:
        return "N/A"
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _format_gps(row: dict[str, str]) -> str:
    """Returns the GPS coordinates of row as 'latitude, longitude' rounded to 4 decimal digits, 'N/A' if missing"""
    lat, lon = _to_float(row.get("gps_latitude")), _to_float(row.get("gps_longitude"))
    return f"{lat:.4f}, {lon:.4f}" if lat is not None and lon is not None else "N/A"


def _print_pair(index: int, total: int, pair: tuple[str, dict[str, str], dict[str, str]], recommended: int | None) -> None:
    """Prints a pair of candidate duplicate photos, with their key metadata, marking the one recommended for deletion"""
    likelihood, row_a, row_b = pair
    print(f"\n[{index}/{total}] duplicate likelihood: {likelihood}%")
    for i, row in ((1, row_a), (2, row_b)):
        mark = "  <<< SUGGESTED FOR DELETION" if i == recommended else ""
        print(f"  [{i}] {row['full_path']}{mark}")
        print(
            f"      size={_format_size(row.get('size_bytes'))}  date_taken={row.get('date_taken') or 'N/A'}  "
            f"device={row.get('device') or 'N/A'}  gps={_format_gps(row)}"
        )
    if recommended is None:
        print("  No recommendation: the 2 photos are equally likely to be the original")


ABORT_ANSWER: str = "q"  # A letter, not a digit, so it can't be hit by mistake while answering 1/2/0


def _ask_which_to_delete(recommended: int | None) -> int | None:
    """Asks the user which of the 2 photos just printed by _print_pair() to delete, returns 1, 2, or 0 for neither,
    or None to stop the whole review gracefully (answering ABORT_ANSWER). Pressing Enter without typing anything
    answers recommended (or 0 if there is none)"""
    default = recommended if recommended is not None else 0
    while True:
        answer = input(f"Delete [1], [2], [0] to keep both, or [{ABORT_ANSWER}] to stop (Enter = {default}): ").strip().lower()
        if answer == "":
            return default
        if answer in ("0", "1", "2"):
            return int(answer)
        if answer == ABORT_ANSWER:
            return None
        print(f"Please answer 1, 2, 0, or {ABORT_ANSWER}")


def _is_local_path(full_path: str) -> bool:
    """Returns whether full_path is a local file path, as opposed to a synthetic 'googlephotos:<id>' identifier (see
    google_photo_row()) that has no existence on disk to check"""
    return not full_path.startswith("googlephotos:")


def _is_missing(full_path: str) -> bool:
    """Returns whether full_path is a local file path (see _is_local_path()) that no longer exists on disk"""
    return _is_local_path(full_path) and not os.path.isfile(full_path)


def _delete_photo(path: str) -> bool:
    """Deletes path from disk, returns True if it was deleted or was already missing (either way, it should no longer
    be in the inventory), False if it exists but could not be deleted (eg permission denied), logging accordingly"""
    try:
        os.remove(path)
        log.logger.info("Deleted %s", path)
        return True
    except FileNotFoundError:
        log.logger.warning("%s was already missing", path)
        return True
    except OSError as e:
        log.logger.warning("Could not delete %s: %s", path, e)
        return False


def _write_dict_rows(rows: list[dict[str, str]], out_file: str) -> None:
    """Writes rows (dicts keyed by CSV_HEADER, as read back by csv.DictReader) to out_file, in CSV_HEADER column order"""
    with open(out_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(CSV_HEADER), dialect="excel", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


def _dedup_pairs(rows: list[dict[str, str]]) -> list[tuple[str, dict[str, str], dict[str, str]]]:
    """Returns the (duplicate_likelihood, row_a, row_b) pairs of rows having a duplicate_likelihood and an existing
    duplicate_of, sorted by decreasing likelihood, each pair appearing once even if both rows point to each other"""
    by_path = {row["full_path"]: row for row in rows}
    seen: set[frozenset[str]] = set()
    pairs: list[tuple[str, dict[str, str], dict[str, str]]] = []
    for row in rows:
        likelihood = row.get("duplicate_likelihood")
        other_path = row.get("duplicate_of")
        if not likelihood or not other_path or other_path not in by_path:
            continue
        key = frozenset((row["full_path"], other_path))
        if key in seen:
            continue
        seen.add(key)
        pairs.append((likelihood, row, by_path[other_path]))
    pairs.sort(key=lambda pair: int(pair[0]), reverse=True)
    return pairs


def _remove_missing(rows: list[dict[str, str]], row_a: dict[str, str], row_b: dict[str, str], csv_file: str, removed_missing: set[str]) -> bool:
    """Removes, from rows and csv_file, whichever of row_a/row_b no longer exists on disk (see _is_missing()), adding
    its full_path to removed_missing, and returns whether any was removed. Called before asking anything about a
    pair: a photo that is already gone leaves nothing to choose between"""
    missing = [row for row in (row_a, row_b) if _is_missing(row["full_path"])]
    if not missing:
        return False
    for row in missing:
        log.logger.info("%s no longer exists on disk, removing it from the inventory", row["full_path"])
        removed_missing.add(row["full_path"])
    rows[:] = [row for row in rows if row["full_path"] not in removed_missing]
    _write_dict_rows(rows, csv_file)
    return True


AUTO_DELETE_LIKELIHOOD: int = 100  # A pair at this duplicate_likelihood is deleted automatically, without asking, see dedup()


def dedup(csv_file: str) -> None:
    """Interactively reviews, from the highest to the lowest duplicate_likelihood, the pairs of photos of csv_file that
    may be duplicates (as computed by add_duplicate_likelihood()), and lets the user delete one of each pair, or
    neither. For each pair, prints their size, date taken, device and GPS coordinates, and suggests which one to
    delete (see _recommend_deletion()). A pair at AUTO_DELETE_LIKELIHOOD (100%) with a recommendation is deleted
    automatically, without asking, since there is no reasonable doubt they are the same photo; every other pair is
    asked about. Before any of that, a pair where one or both photos no longer exist on disk (eg already deleted or
    moved outside the inventoried tree since it was built) is never asked about either: the missing one (or both, if
    neither exists) is simply removed from csv_file, since there is nothing left to choose between. A photo chosen
    for deletion is removed from disk and, whether it was actually deleted or was already missing, also from
    csv_file (which is written back after each removal so an interrupted review can be resumed later without
    re-reviewing already handled pairs); it is kept in csv_file if it exists but could not be deleted. Answering
    ABORT_ANSWER to a question stops the review right away, keeping every pair not yet handled in csv_file"""
    with open(csv_file, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not any(row.get("duplicate_likelihood") for row in rows):
        log.logger.error("%s has no duplicate_likelihood column: run 'imagetool inventory -i %s' first", csv_file, csv_file)
        sys.exit(1)
    pairs = _dedup_pairs(rows)
    total = len(pairs)
    print(f"{total} potential duplicate pair(s) to review, highest likelihood first")
    deleted: set[str] = set()
    removed_missing: set[str] = set()
    for index, pair in enumerate(pairs, start=1):
        likelihood, row_a, row_b = pair
        if row_a["full_path"] in deleted or row_b["full_path"] in deleted:
            continue
        if _remove_missing(rows, row_a, row_b, csv_file, removed_missing):
            deleted |= removed_missing
            continue
        recommended = _recommend_deletion(row_a, row_b)
        _print_pair(index, total, pair, recommended)
        if recommended is not None and int(likelihood) >= AUTO_DELETE_LIKELIHOOD:
            print(f"  100% match: automatically deleting [{recommended}]")
            choice = recommended
        else:
            choice = _ask_which_to_delete(recommended)
        if choice is None:
            print("Stopping the review")
            break
        if choice == 0:
            continue
        to_delete = row_a if choice == 1 else row_b
        if not _delete_photo(to_delete["full_path"]):
            continue
        deleted.add(to_delete["full_path"])
        rows = [row for row in rows if row["full_path"] != to_delete["full_path"]]
        _write_dict_rows(rows, csv_file)
    print(f"{len(deleted) - len(removed_missing)} photo(s) deleted, {len(removed_missing)} already missing from disk removed from the inventory")


def _file_dates(filename: str) -> tuple[int | None, str | None, str | None]:
    """Returns the (size in bytes, creation date, modification date) of a file, None values if it can't be stat'ed"""
    try:
        st = os.stat(filename)
    except OSError as e:
        log.logger.warning("Could not read the file info of %s: %s", filename, e)
        return None, None, None
    return st.st_size, datetime.fromtimestamp(st.st_ctime).strftime(DATE_FMT), datetime.fromtimestamp(st.st_mtime).strftime(DATE_FMT)


# Date/time encoded in a file name, as (regex, strptime format) pairs tried from the most to the least specific; the
# regex's whole match is fed to strptime. Covers the date_time-bearing patterns of _ORIGINAL_FILENAME_PATTERNS (eg
# IMG_20180706_125922, PXL_20210101_123456, PANO_20190415_103823, 20130804_174038, signal-2020-01-01-123456,
# IMG-20200101-WA0001), plus "25-12-2011 16-46-10_0021"
_FILENAME_DATE_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\d{2}-\d{2}-\d{4} \d{2}-\d{2}-\d{2}"), "%d-%m-%Y %H-%M-%S"),
    (re.compile(r"\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2}"), "%Y-%m-%d %H.%M.%S"),
    (re.compile(r"\d{4}-\d{2}-\d{2}-\d{6}"), "%Y-%m-%d-%H%M%S"),
    (re.compile(r"\d{8}_\d{6}"), "%Y%m%d_%H%M%S"),
    (re.compile(r"\d{8}"), "%Y%m%d"),
)


def _date_from_filename(file_name: str) -> str | None:
    """Returns the date (and time, when the file name encodes one) guessed from file_name, as a fallback date taken
    when there is no EXIF (or, for a Google Photos item, API) date to use instead. Tries _FILENAME_DATE_PATTERNS
    from the most to the least specific, the first one that both matches and parses to a valid date wins, None if
    none does"""
    stem = os.path.splitext(file_name)[0]
    for pattern, fmt in _FILENAME_DATE_PATTERNS:
        match = pattern.search(stem)
        if match:
            try:
                return datetime.strptime(match.group(), fmt).strftime(DATE_FMT)
            except ValueError:
                continue
    return None


def _resolve_date_taken(exif_date: datetime | None, file_name: str, date_created: str | None, date_modified: str | None) -> str | None:
    """Returns the best available date a photo was taken: its EXIF date when it has one, else the date guessed from
    its file name (see _date_from_filename()), else its own file creation date, falling back to its modification
    date; None if none of these is available"""
    if exif_date:
        return exif_date.strftime(DATE_FMT)
    return _date_from_filename(file_name) or date_created or date_modified


def photo_row(et: ExifToolHelper, filename: str) -> list[object]:
    """Returns the row (in PHOTO_CSV_HEADER order) of a photo, with its EXIF data read with an already open ExifToolHelper
    (a single exiftool process is kept open for a whole chunk of photos, see inventory()). date_taken falls back to
    the date guessed from the file name, then to the file's own creation/modification date (see
    _resolve_date_taken()), when the photo has no EXIF date of its own"""
    try:
        exif_data = et.get_metadata(filename)[0]
    except Exception as e:
        log.logger.warning("Could not read the EXIF data of %s: %s", filename, e)
        exif_data = {}
    width, height = _get_dimensions(exif_data)
    lat, lon, alt = _get_gps(exif_data)
    date_taken = _get_date_taken(exif_data)
    size_bytes, date_created, date_modified = _file_dates(filename)
    file_name = fil.basename(filename, strip_ext=False)
    return [
        os.path.abspath(filename),
        file_name,
        size_bytes,
        width,
        height,
        compute_fingerprint(filename),
        _resolve_date_taken(date_taken, file_name, date_created, date_modified),
        date_created,
        date_modified,
        lat,
        lon,
        alt,
        _get_device(exif_data),
        exif_data.get("EXIF:LensModel"),
        exif_data.get("EXIF:ISO"),
        exif_data.get("EXIF:FNumber"),
        exif_data.get("EXIF:ExposureTime"),
        exif_data.get("EXIF:FocalLength"),
        exif_data.get("EXIF:Orientation"),
        exif_data.get("EXIF:Software"),
    ]


def _chunks(files: list[str], nb_chunks: int) -> list[list[str]]:
    """Splits the files into nb_chunks chunks of (almost) equal size, preserving their order"""
    size = max(1, -(-len(files) // nb_chunks))
    chunks = []
    for start in range(0, len(files), size):
        stop = start + size
        chunks.append(files[start:stop])
    return chunks


def _load_reusable_rows(out_file: str) -> tuple[dict[str, list[object]], float | None]:
    """Returns ({full_path: row}, the modification time) of an existing inventory CSV already at out_file, used by
    inventory() to reuse the fingerprint and metadata of a photo that has not changed since it was written, instead
    of recomputing them. ({}, None) if out_file does not exist yet"""
    if not os.path.isfile(out_file):
        return {}, None
    full_path_idx = PHOTO_CSV_HEADER.index("full_path")
    rows = _read_inventory_csv(out_file)
    return {row[full_path_idx]: row for row in rows}, os.path.getmtime(out_file)


def _reusable_row(filename: str, reusable: dict[str, list[object]], csv_mtime: float | None) -> list[object] | None:
    """Returns the row already in reusable (see _load_reusable_rows()) for filename, if it has not been modified
    since csv_mtime (the existing CSV's own modification time), None if it must be (re)computed instead: it is new,
    it was modified since, or there is no existing CSV (csv_mtime is None)"""
    if csv_mtime is None:
        return None
    existing = reusable.get(os.path.abspath(filename))
    if existing is None:
        return None
    try:
        if os.path.getmtime(filename) > csv_mtime:
            return None
    except OSError:
        return None
    return existing


def _process_chunk(
    files: list[str],
    progress_done: Callable[[], None],
    reusable: dict[str, list[object]] | None = None,
    csv_mtime: float | None = None,
) -> list[list[object]]:
    """Returns the CSV rows of a chunk of photos, their EXIF data read with a single exiftool process kept open for the whole
    chunk: spawning one exiftool process per photo, instead of per chunk, would make the inventory of a large photo
    collection much slower. A photo already in reusable that has not changed since csv_mtime (see _reusable_row()) reuses
    its existing row as-is, without recomputing its fingerprint or metadata. progress_done() is called after each photo,
    not only once the whole chunk is done, so the progress is reported as the photos are actually processed, not in
    bursts of a whole chunk at a time"""
    rows = []
    with ExifToolHelper(executable=util.get_exiftool(), common_args=util.EXIFTOOL_ARGS, encoding="utf-8") as et:
        for f in files:
            row = _reusable_row(f, reusable or {}, csv_mtime)
            rows.append(row if row is not None else photo_row(et, f))
            progress_done()
    return rows


def inventory(files: list[str], out_file: str, max_workers: int = DEFAULT_WORKERS) -> int:
    """Writes a CSV inventory of the photos (full path, size, dimensions, a perceptual fingerprint, dates, GPS coordinates,
    device, other common EXIF metadata and a duplicate likelihood with the most similar other photo) to out_file. The
    photos are read in parallel, max_workers threads each reading a chunk of them with its own exiftool process. If
    out_file already exists (eg a previous run over the same directory/drive), a photo that has not changed since
    then (see _reusable_row()) reuses its fingerprint and metadata from it, instead of recomputing them: only the new
    or modified photos are actually read. The progress and the ETA are logged at most every PROGRESS_PERIOD seconds.
    Returns the number of photos inventoried"""
    total = len(files)
    progress_done = _progress_logger(total)
    log.logger.info("Inventorying %d photos into %s", total, out_file)
    reusable, csv_mtime = _load_reusable_rows(out_file)
    if reusable:
        log.logger.info("Reusing the metadata already in %s for the photos that have not changed since", out_file)
    chunks = _chunks(files, max(1, min(max_workers, total)))
    rows: list[list[object]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="PhotoInventory") as executor:
        futures = [executor.submit(_process_chunk, chunk, progress_done, reusable, csv_mtime) for chunk in chunks]
        for future in concurrent.futures.as_completed(futures):
            rows.extend(future.result())
    log.logger.info("Computing the duplicate likelihood of %d photos...", total)
    add_duplicate_likelihood(rows)
    _write_csv(rows, out_file)
    log.logger.info("Inventory of %d photos written to %s", total, out_file)
    return total


DEFAULT_GOOGLE_OUTPUT: str = "google-photos-inventory.csv"
GOOGLE_FINGERPRINT_PARAMS: str = f"=w{FINGERPRINT_GRID + 1}-h{FINGERPRINT_GRID}"  # Resizes the thumbnail to compute_fingerprint()'s grid


def _default_pictures_dir() -> str:
    r"""Returns the OS default directory for pictures (eg 'C:\Users\<user>\Pictures' on Windows), used to default
    the output of --google since there is no input directory to default it from"""
    return os.path.join(os.path.expanduser("~"), "Pictures")


def _google_dimensions(media_file_metadata: dict[str, object]) -> tuple[int | None, int | None]:
    """Returns the (width, height) of a picked Google Photos media item, from its mediaFileMetadata, (None, None) if missing"""
    width, height = media_file_metadata.get("width"), media_file_metadata.get("height")
    return (int(width), int(height)) if width and height else (None, None)


def _google_device(photo_metadata: dict[str, object]) -> str | None:
    """Returns the device (make and model) that took a picked Google Photos media item, from its photoMetadata, None if there is none"""
    make = str(photo_metadata.get("cameraMake", "")).strip()
    model = str(photo_metadata.get("cameraModel", "")).strip()
    return f"{make} {model}".strip() or None


def _google_date_taken(item: dict[str, object]) -> str | None:
    """Returns the date a picked Google Photos media item was created (its closest available equivalent to the date a
    photo was taken), from its createTime, None if missing or not parseable"""
    create_time = item.get("createTime")
    if not create_time:
        return None
    try:
        return datetime.strptime(str(create_time), "%Y-%m-%dT%H:%M:%SZ").strftime(DATE_FMT)
    except ValueError:
        return None


def _parse_http_date(value: str | None) -> str | None:
    """Returns an HTTP date header value (eg 'Wed, 21 Oct 2015 07:28:00 GMT', as found in a Last-Modified header)
    reformatted to DATE_FMT, None if value is missing or not parseable"""
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).strftime(DATE_FMT)
    except (TypeError, ValueError):
        return None


def google_photo_row(access_token: str, item: dict[str, object]) -> list[object]:
    """Returns the row (in PHOTO_CSV_HEADER order) of a photo picked from a Google Photos library (see
    google_photos.list_picked_media_items()). Its full_path is a synthetic 'googlephotos:<id>' identifier (there is
    no local file), and the columns the Picker API does not expose for a picked photo (GPS coordinates, the file's
    own creation/modification dates, lens model, orientation, software) are left empty. date_taken falls back to the
    date guessed from the file name (see _date_from_filename()), then to the Last-Modified HTTP header of the
    original file (the closest available equivalent to a local file's own creation date), when the item's
    createTime is missing"""
    media_file = item.get("mediaFile", {})
    metadata = media_file.get("mediaFileMetadata", {})
    photo_metadata = metadata.get("photoMetadata", {})
    base_url = media_file.get("baseUrl")
    file_name = media_file.get("filename")
    width, height = _google_dimensions(metadata)
    fingerprint = None
    size_bytes = None
    date_taken = _google_date_taken(item) or (_date_from_filename(file_name) if file_name else None)
    if base_url:
        data = google_photos.fetch_bytes(access_token, base_url, GOOGLE_FINGERPRINT_PARAMS)
        if data is not None:
            fingerprint = compute_fingerprint_from_bytes(data, file_name or str(item.get("id")))
        size_bytes = google_photos.fetch_size(access_token, base_url)
        if date_taken is None:
            date_taken = _parse_http_date(google_photos.fetch_last_modified(access_token, base_url))
    return [
        f"googlephotos:{item.get('id')}",
        file_name,
        size_bytes,
        width,
        height,
        fingerprint,
        date_taken,
        None,
        None,
        None,
        None,
        None,
        _google_device(photo_metadata),
        None,
        photo_metadata.get("isoEquivalent"),
        photo_metadata.get("apertureFNumber"),
        photo_metadata.get("exposureTime"),
        photo_metadata.get("focalLength"),
        None,
        None,
    ]


def _process_google_item(access_token: str, item: dict[str, object], progress_done: Callable[[], None]) -> list[object]:
    """Returns the CSV row of one Google Photos item picked by the user, and records its progress"""
    row = google_photo_row(access_token, item)
    progress_done()
    return row


def _existing_full_paths(out_file: str) -> set[str]:
    """Returns the full_path of every photo already inventoried in out_file, an empty set if it doesn't exist yet"""
    if not os.path.isfile(out_file):
        return set()
    with open(out_file, newline="", encoding="utf-8") as fh:
        return {row["full_path"] for row in csv.DictReader(fh) if row.get("full_path")}


def google_inventory(out_file: str, max_workers: int = DEFAULT_WORKERS) -> int:
    """Lets the user pick, through the Google Photos picker UI opened in their browser, the photos and/or albums of
    their Google Photos library to inventory, then writes a CSV inventory of them (same columns as inventory(), with
    the ones the Picker API does not expose for a picked photo left empty, see google_photo_row()) to out_file. If
    out_file already exists (eg from an earlier run, since the picker only lets you select a limited number of
    photos at a time), it is extended rather than replaced: a picked photo already in it (by its full_path) is
    skipped, not fetched nor added again, and the duplicate likelihood is recomputed across the whole, now larger,
    CSV. Returns the number of (new) photos inventoried, 0 if every picked photo was already in out_file. Exits with
    code 1 if nothing was picked"""
    access_token = google_photos.get_access_token()
    session = google_photos.create_picker_session(access_token)
    session = google_photos.wait_for_selection(access_token, session)
    items = list(google_photos.list_picked_media_items(access_token, session["id"]))
    google_photos.delete_picker_session(access_token, session["id"])
    if not items:
        log.logger.error("No photo was picked in the Google Photos picker")
        sys.exit(1)
    existing_paths = _existing_full_paths(out_file)
    new_items = [item for item in items if f"googlephotos:{item.get('id')}" not in existing_paths]
    skipped = len(items) - len(new_items)
    if skipped:
        log.logger.info("%d of the %d picked photos are already in %s, skipping them", skipped, len(items), out_file)
    if not new_items:
        log.logger.info("Nothing new to inventory: all %d picked photos are already in %s", len(items), out_file)
        return 0
    total = len(new_items)
    progress_done = _progress_logger(total)
    log.logger.info("Inventorying %d photos picked from Google Photos into %s", total, out_file)
    rows: list[list[object]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="GooglePhotoInventory") as executor:
        futures = [executor.submit(_process_google_item, access_token, item, progress_done) for item in new_items]
        rows.extend(future.result() for future in concurrent.futures.as_completed(futures))
    if existing_paths:
        rows = _read_inventory_csv(out_file) + rows
    log.logger.info("Computing the duplicate likelihood of %d photos...", len(rows))
    add_duplicate_likelihood(rows)
    _write_csv(rows, out_file)
    log.logger.info("Inventory of %d new Google Photos photos added to %s (%d total)", total, out_file, len(rows))
    return total


def main() -> None:
    """Inventories the photos found in directories, disk drives and/or files given in -i into a CSV file. -i can instead be
    a single, already existing inventory CSV file: its duplicate_likelihood and duplicate_of columns are then (re)computed
    from the metadata and fingerprints it already has, without rescanning any photo. With --dedup, -i must be such a CSV
    file, already having its duplicate_likelihood computed: the likely duplicates it lists are then interactively
    reviewed, highest likelihood first, and the chosen one of each pair deleted, see dedup(). With --google, -i is not
    used: the photos are picked from a Google Photos library instead, see google_inventory()"""
    util.init("image-inventory")
    parser = argparse.ArgumentParser(description="Inventories photos (size, dimensions, dates, GPS coordinates, device...) into a CSV file")
    util.add_input_args(
        parser,
        "Directories, disk drives and/or photo files to inventory (directories are scanned recursively), "
        "or a single existing inventory CSV file to only (re)compute the duplicate likelihood of. Not used with --google",
        required=False,
    )
    util.add_output_args(
        parser,
        f"CSV file to write (default: {DEFAULT_OUTPUT}, or the input CSV file itself when -i is one, or "
        f"<Pictures>/{DEFAULT_GOOGLE_OUTPUT} with --google)",
    )
    util.add_verbosity_arg(parser)
    parser.add_argument(
        "--threads", type=int, default=DEFAULT_WORKERS, help=f"Number of threads reading the photos metadata in parallel (default: {DEFAULT_WORKERS})"
    )
    parser.add_argument(
        "--dedup",
        action="store_true",
        help="Interactively review the pairs of likely duplicate photos of an existing inventory CSV given in -i, from the "
        "highest duplicate_likelihood down, and delete one of each pair (or neither)",
    )
    parser.add_argument(
        "--google",
        action="store_true",
        help="Inventory photos picked from a Google Photos library instead of local files: a browser page lets you pick "
        "the photos/albums to inventory (see docs/imagetool-inventory.md for the one-time Google OAuth2 setup needed). "
        "-i is not used",
    )
    kwargs = util.parse_media_args(parser, input_type=fil.FileType.IMAGE_FILE, expand_inputs=False)
    inputs = kwargs.get(util.INPUT_FILES, [])

    if kwargs.get("google"):
        out_file = kwargs.get(util.OUTPUT_FILE) or os.path.join(_default_pictures_dir(), DEFAULT_GOOGLE_OUTPUT)
        nb_photos = google_inventory(out_file, max_workers=kwargs.get("threads", DEFAULT_WORKERS))
        util.generated_file(out_file)
        log.logger.info("%d photos inventoried", nb_photos)
        return

    if kwargs.get("dedup"):
        if len(inputs) != 1 or not inputs[0].lower().endswith(".csv") or not os.path.isfile(inputs[0]):
            log.logger.error("--dedup requires a single existing inventory CSV file as -i")
            sys.exit(1)
        dedup(inputs[0])
        return

    if not inputs:
        log.logger.error("-i is required unless --google is given")
        sys.exit(1)

    if len(inputs) == 1 and inputs[0].lower().endswith(".csv") and os.path.isfile(inputs[0]):
        out_file = kwargs.get(util.OUTPUT_FILE) or inputs[0]
        rows = _read_inventory_csv(inputs[0])
        log.logger.info("Computing the duplicate likelihood of %d photos read from %s...", len(rows), inputs[0])
        add_duplicate_likelihood(rows)
        _write_csv(rows, out_file)
        nb_photos = len(rows)
    else:
        out_file = kwargs.get(util.OUTPUT_FILE) or DEFAULT_OUTPUT
        photos = _collect_photos(inputs)
        nb_photos = inventory(photos, out_file, max_workers=kwargs.get("threads", DEFAULT_WORKERS))
    util.generated_file(out_file)
    log.logger.info("%d photos inventoried", nb_photos)


if __name__ == "__main__":
    main()
