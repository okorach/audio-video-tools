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

"""Tool that inventories the photos found in directories and/or disk drives into a CSV file: full path, short name, size,
dimensions, a perceptual fingerprint, dates (taken, created, modified), GPS coordinates, device and other common EXIF
metadata, and a duplicate likelihood (how much a photo looks like another one of the inventory, based on its fingerprint
and its metadata) to help detect duplicates and near-duplicates"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import itertools
import os
import sys
import threading
import time
from datetime import datetime
from typing import TYPE_CHECKING

from exiftool import ExifToolHelper
from PIL import Image, ImageOps

import mediatools.utilities as util
import utilities.file as fil
from mediatools import log

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


def _is_excluded(filename: str) -> bool:
    """Returns whether filename has one of the EXCLUDED_EXTENSIONS, always skipped by the inventory"""
    return filename.lower().rsplit(".", 1)[-1] in EXCLUDED_EXTENSIONS


def _collect_photos(paths: list[str]) -> list[str]:
    """Expands the files, directories and/or disk drives given in paths into the list of photos they contain (directories are
    walked recursively, files are kept as given whatever their extension, except EXCLUDED_EXTENSIONS which are always skipped).
    Logs the number of photos collected so far every COLLECT_PROGRESS_PERIOD seconds, since walking a whole disk drive can take
    a while before the inventory itself starts. Exits with code 1 if no photo is found"""
    files: list[str] = []
    last_log = time.monotonic()
    for path in paths:
        if not os.path.isdir(path):
            if not _is_excluded(path):
                files.append(path)
            continue
        for root, _, names in os.walk(path):
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


def compute_fingerprint(filename: str) -> str | None:
    """Returns a perceptual fingerprint of a photo, as a hex string, computed only from its pixels (not from its file name
    or its metadata): a difference hash of a small grayscale thumbnail of the photo (after applying its EXIF orientation),
    so that it is identical for the exact same image, and close (small hamming_distance()) for the same image resized or
    cropped a bit, which can later be used to compute a match probability between two photos. None if the photo can't be
    read as an image"""
    try:
        with Image.open(filename) as img:
            nb_pixels = img.width * img.height
            if Image.MAX_IMAGE_PIXELS and nb_pixels > Image.MAX_IMAGE_PIXELS:
                # Pillow itself only warns about this (without naming the file), decoding such a large image may be slow
                log.logger.warning("%s is a very large image (%d pixels), its fingerprint may take a while to compute", filename, nb_pixels)
            resample = getattr(Image, "Resampling", Image).LANCZOS
            thumbnail = ImageOps.exif_transpose(img).convert("L").resize((FINGERPRINT_GRID + 1, FINGERPRINT_GRID), resample)
            pixels = list(getattr(thumbnail, "get_flattened_data", thumbnail.getdata)())
    except Exception as e:
        log.logger.warning("Could not compute the fingerprint of %s: %s", filename, e)
        return None
    width = FINGERPRINT_GRID + 1
    bits = "".join(
        "1" if pixels[row * width + col] > pixels[row * width + col + 1] else "0"
        for row in range(FINGERPRINT_GRID)
        for col in range(FINGERPRINT_GRID)
    )
    return f"{int(bits, 2):0{len(bits) // 4}x}"


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


def _file_dates(filename: str) -> tuple[int | None, str | None, str | None]:
    """Returns the (size in bytes, creation date, modification date) of a file, None values if it can't be stat'ed"""
    try:
        st = os.stat(filename)
    except OSError as e:
        log.logger.warning("Could not read the file info of %s: %s", filename, e)
        return None, None, None
    return st.st_size, datetime.fromtimestamp(st.st_ctime).strftime(DATE_FMT), datetime.fromtimestamp(st.st_mtime).strftime(DATE_FMT)


def photo_row(et: ExifToolHelper, filename: str) -> list[object]:
    """Returns the row (in PHOTO_CSV_HEADER order) of a photo, with its EXIF data read with an already open ExifToolHelper
    (a single exiftool process is kept open for a whole chunk of photos, see inventory())"""
    try:
        exif_data = et.get_metadata(filename)[0]
    except Exception as e:
        log.logger.warning("Could not read the EXIF data of %s: %s", filename, e)
        exif_data = {}
    width, height = _get_dimensions(exif_data)
    lat, lon, alt = _get_gps(exif_data)
    date_taken = _get_date_taken(exif_data)
    size_bytes, date_created, date_modified = _file_dates(filename)
    return [
        os.path.abspath(filename),
        fil.basename(filename, strip_ext=False),
        size_bytes,
        width,
        height,
        compute_fingerprint(filename),
        date_taken.strftime(DATE_FMT) if date_taken else None,
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


def _process_chunk(files: list[str], progress_done: Callable[[], None]) -> list[list[object]]:
    """Returns the CSV rows of a chunk of photos, their EXIF data read with a single exiftool process kept open for the whole
    chunk: spawning one exiftool process per photo, instead of per chunk, would make the inventory of a large photo
    collection much slower. progress_done() is called after each photo, not only once the whole chunk is done, so the
    progress is reported as the photos are actually processed, not in bursts of a whole chunk at a time"""
    rows = []
    with ExifToolHelper(executable=util.get_exiftool(), common_args=util.EXIFTOOL_ARGS, encoding="utf-8") as et:
        for f in files:
            rows.append(photo_row(et, f))
            progress_done()
    return rows


def inventory(files: list[str], out_file: str, max_workers: int = DEFAULT_WORKERS) -> int:
    """Writes a CSV inventory of the photos (full path, size, dimensions, a perceptual fingerprint, dates, GPS coordinates,
    device, other common EXIF metadata and a duplicate likelihood with the most similar other photo) to out_file. The
    photos are read in parallel, max_workers threads each reading a chunk of them with its own exiftool process. The
    progress and the ETA are logged at most every PROGRESS_PERIOD seconds. Returns the number of photos inventoried"""
    total = len(files)
    progress_done = _progress_logger(total)
    log.logger.info("Inventorying %d photos into %s", total, out_file)
    chunks = _chunks(files, max(1, min(max_workers, total)))
    rows: list[list[object]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="PhotoInventory") as executor:
        futures = [executor.submit(_process_chunk, chunk, progress_done) for chunk in chunks]
        for future in concurrent.futures.as_completed(futures):
            rows.extend(future.result())
    log.logger.info("Computing the duplicate likelihood of %d photos...", total)
    add_duplicate_likelihood(rows)
    _write_csv(rows, out_file)
    log.logger.info("Inventory of %d photos written to %s", total, out_file)
    return total


def main() -> None:
    """Inventories the photos found in directories, disk drives and/or files given in -i into a CSV file. -i can instead be
    a single, already existing inventory CSV file: its duplicate_likelihood and duplicate_of columns are then (re)computed
    from the metadata and fingerprints it already has, without rescanning any photo"""
    util.init("image-inventory")
    parser = argparse.ArgumentParser(description="Inventories photos (size, dimensions, dates, GPS coordinates, device...) into a CSV file")
    util.add_input_args(
        parser,
        "Directories, disk drives and/or photo files to inventory (directories are scanned recursively), "
        "or a single existing inventory CSV file to only (re)compute the duplicate likelihood of",
    )
    util.add_output_args(parser, f"CSV file to write (default: {DEFAULT_OUTPUT}, or the input CSV file itself when -i is one)")
    util.add_verbosity_arg(parser)
    parser.add_argument(
        "--threads", type=int, default=DEFAULT_WORKERS, help=f"Number of threads reading the photos metadata in parallel (default: {DEFAULT_WORKERS})"
    )
    kwargs = util.parse_media_args(parser, input_type=fil.FileType.IMAGE_FILE, expand_inputs=False)
    inputs = kwargs[util.INPUT_FILES]

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
