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
dimensions, a perceptual fingerprint (to later detect duplicates), dates (taken, created, modified), GPS coordinates, device
and other common EXIF metadata"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
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

CSV_HEADER: tuple[str, ...] = (
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


def _collect_photos(paths: list[str]) -> list[str]:
    """Expands the files, directories and/or disk drives given in paths into the list of photos they contain (directories are
    walked recursively, files are kept as given whatever their extension). Logs the number of photos collected so far every
    COLLECT_PROGRESS_PERIOD seconds, since walking a whole disk drive can take a while before the inventory itself starts.
    Exits with code 1 if no photo is found"""
    files: list[str] = []
    last_log = time.monotonic()
    for path in paths:
        if not os.path.isdir(path):
            files.append(path)
            continue
        for root, _, names in os.walk(path):
            for name in names:
                if not fil.is_image_file(name):
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


def _file_dates(filename: str) -> tuple[int | None, str | None, str | None]:
    """Returns the (size in bytes, creation date, modification date) of a file, None values if it can't be stat'ed"""
    try:
        st = os.stat(filename)
    except OSError as e:
        log.logger.warning("Could not read the file info of %s: %s", filename, e)
        return None, None, None
    return st.st_size, datetime.fromtimestamp(st.st_ctime).strftime(DATE_FMT), datetime.fromtimestamp(st.st_mtime).strftime(DATE_FMT)


def photo_row(et: ExifToolHelper, filename: str) -> list[object]:
    """Returns the CSV row (in CSV_HEADER order) of a photo, with its EXIF data read with an already open ExifToolHelper
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
    collection much slower"""
    with ExifToolHelper(executable=util.get_exiftool(), common_args=util.EXIFTOOL_ARGS, encoding="utf-8") as et:
        rows = [photo_row(et, f) for f in files]
    for _ in files:
        progress_done()
    return rows


def inventory(files: list[str], out_file: str, max_workers: int = DEFAULT_WORKERS) -> int:
    """Writes a CSV inventory of the photos (full path, size, dimensions, a perceptual fingerprint, dates, GPS coordinates,
    device and other common EXIF metadata) to out_file. The photos are read in parallel, max_workers threads each reading a
    chunk of them with its own exiftool process. The progress and the ETA are logged at most every PROGRESS_PERIOD seconds.
    Returns the number of photos inventoried"""
    total = len(files)
    progress_done = _progress_logger(total)
    log.logger.info("Inventorying %d photos into %s", total, out_file)
    chunks = _chunks(files, max(1, min(max_workers, total)))
    with open(out_file, "w", newline="", encoding="utf-8") as fh:
        csv_writer = csv.writer(fh, dialect="excel", quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(CSV_HEADER)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="PhotoInventory") as executor:
            futures = [executor.submit(_process_chunk, chunk, progress_done) for chunk in chunks]
            for future in concurrent.futures.as_completed(futures):
                for row in future.result():
                    csv_writer.writerow(row)
    log.logger.info("Inventory of %d photos written to %s", total, out_file)
    return total


def main() -> None:
    """Inventories the photos found in directories, disk drives and/or files given in -i into a CSV file"""
    util.init("image-inventory")
    parser = argparse.ArgumentParser(description="Inventories photos (size, dimensions, dates, GPS coordinates, device...) into a CSV file")
    util.add_input_args(parser, "Directories, disk drives and/or photo files to inventory (directories are scanned recursively)")
    util.add_output_args(parser, f"CSV file to write (default: {DEFAULT_OUTPUT})")
    util.add_verbosity_arg(parser)
    parser.add_argument(
        "--threads", type=int, default=DEFAULT_WORKERS, help=f"Number of threads reading the photos metadata in parallel (default: {DEFAULT_WORKERS})"
    )
    kwargs = util.parse_media_args(parser, input_type=fil.FileType.IMAGE_FILE, expand_inputs=False)

    out_file = kwargs.get(util.OUTPUT_FILE) or DEFAULT_OUTPUT
    photos = _collect_photos(kwargs[util.INPUT_FILES])
    nb_photos = inventory(photos, out_file, max_workers=kwargs.get("threads", DEFAULT_WORKERS))
    util.generated_file(out_file)
    log.logger.info("%d photos inventoried", nb_photos)


if __name__ == "__main__":
    main()
