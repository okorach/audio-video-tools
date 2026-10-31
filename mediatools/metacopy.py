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

"""Copies the creation date and the geotagging (GPS coordinates) of a source media file to a file generated from it,
and keeps the dates of the files modified in place"""

import contextlib
import functools
import os
import re
from collections.abc import Callable, Iterator
from datetime import datetime
from exiftool import ExifToolHelper
import mediatools.utilities as util
import utilities.file as fil
from mediatools import log

QUICKTIME_DATE_TAGS = ("CreateDate", "ModifyDate", "TrackCreateDate", "TrackModifyDate", "MediaCreateDate", "MediaModifyDate")
QUICKTIME_EXTENSIONS = ("mp4", "m4v", "m4a", "mov", "qt", "3gp", "3g2")
OTHER_AUDIO_EXTENSIONS = ("wav", "flac", "ogg", "opus", "aac", "wma", "aiff", "aif")
GPS_KEYS = ("Composite:GPSLatitude", "Composite:GPSLongitude", "Composite:GPSAltitude")
FFMPEG_INPUT_RE = re.compile(r'-i\s+(?:"([^"]+)"|(\S+))')


def find_output_file(ffmpeg_params: str) -> str | None:
    """The output file of an ffmpeg command is its last parameter: a quoted string, or a word"""
    params = ffmpeg_params.strip()
    if params.endswith('"'):
        opening = params.rfind('"', 0, len(params) - 1)
        if 0 <= opening < len(params) - 2:
            content_start = opening + 1
            return params[content_start:-1]
    return params.rsplit(None, 1)[-1] if params else None


def is_media_file(filename: str) -> bool:
    """Returns True if the file is an existing audio, video or image file"""
    known_type = fil.get_type(filename) in (fil.FileType.AUDIO_FILE, fil.FileType.VIDEO_FILE, fil.FileType.IMAGE_FILE)
    return (known_type or fil.extension(filename).lower() in OTHER_AUDIO_EXTENSIONS) and os.path.isfile(filename)


def find_source_and_target(ffmpeg_params: str) -> tuple[str | None, str | None]:
    """Extracts from the parameters of an ffmpeg command the first input that is a media file (the source) and the output file (the target).
    Returns (None, None) if there is no such pair, eg for commands that generate no media file"""
    target = find_output_file(ffmpeg_params)
    if not target or not is_media_file(target):
        return None, None
    for m in FFMPEG_INPUT_RE.finditer(ffmpeg_params):
        source = m.group(1) or m.group(2)
        if is_media_file(source) and os.path.abspath(source) != os.path.abspath(target):
            return source, target
    return None, None


def _get_gps(exif_data: dict) -> tuple[float, float, float | None] | None:
    """Returns the (latitude, longitude, altitude) from the exiftool data read with numeric values (altitude may be None)"""
    try:
        lat, lon = float(exif_data[GPS_KEYS[0]]), float(exif_data[GPS_KEYS[1]])
    except (KeyError, TypeError, ValueError):
        return None
    alt = exif_data.get(GPS_KEYS[2])
    return lat, lon, float(alt) if isinstance(alt, (int, float)) else None


def _set_tags(et: ExifToolHelper, target: str, tags: dict) -> None:
    """Sets tags of a file with exiftool, without changing the file dates. A failure is logged and ignored"""
    try:
        et.set_tags([target], tags=tags, params=["-P", "-overwrite_original"])
    except Exception as e:
        log.logger.debug("Could not set %s on %s: %s", ", ".join(tags), target, e)


def _set_dates(et: ExifToolHelper, target: str, date_str: str) -> None:
    """Sets the dates of a file: the EXIF or QuickTime dates according to its format, then the dates of the file itself"""
    ext = fil.extension(target).lower()
    if fil.get_type(target) == fil.FileType.IMAGE_FILE:
        _set_tags(et, target, {"EXIF:DateTimeOriginal": date_str, "EXIF:CreateDate": date_str, "EXIF:ModifyDate": date_str})
    elif ext in QUICKTIME_EXTENSIONS:
        tags = {f"QuickTime:{t}": date_str for t in QUICKTIME_DATE_TAGS}
        _set_tags(et, target, tags)
    # The dates of the file itself are set last as modifying the file would change them
    _set_tags(et, target, {"File:FileModifyDate": date_str})
    _set_tags(et, target, {"File:FileCreateDate": date_str})


def _set_gps(et: ExifToolHelper, target: str, gps: tuple[float, float, float | None]) -> None:
    """Sets the GPS coordinates (and altitude) of an image, or of a QuickTime file. The other formats can't hold them"""
    lat, lon, alt = gps
    if fil.get_type(target) == fil.FileType.IMAGE_FILE:
        tags = {
            "EXIF:GPSLatitude": abs(lat),
            "EXIF:GPSLatitudeRef": "S" if lat < 0 else "N",
            "EXIF:GPSLongitude": abs(lon),
            "EXIF:GPSLongitudeRef": "W" if lon < 0 else "E",
        }
        if alt is not None:
            tags.update({"EXIF:GPSAltitude": abs(alt), "EXIF:GPSAltitudeRef": 1 if alt < 0 else 0})
        _set_tags(et, target, tags)
    elif fil.extension(target).lower() in QUICKTIME_EXTENSIONS:
        coordinates = f"{lat} {lon}" if alt is None else f"{lat} {lon} {alt}"
        _set_tags(et, target, {"Keys:GPSCoordinates#": coordinates})
    else:
        log.logger.debug("Geotagging is not supported for %s", target)


def copy_date_and_geotag(source: str, target: str) -> None:
    """Gives to the target file the creation date and the GPS coordinates of the source file, when it has some.
    This never fails: the files formats that can't hold these metadata are left as is"""
    try:
        with ExifToolHelper(executable=util.get_exiftool(), common_args=util.EXIFTOOL_ARGS, encoding="utf-8") as et:
            exif_data = et.get_metadata(source, params=["-n"])[0]
            creation_date = util.get_creation_date(exif_data)
            gps = _get_gps(exif_data)
            if gps is not None:
                _set_gps(et, target, gps)
            if creation_date is not None:
                _set_dates(et, target, creation_date.strftime(util.EXIF_DATE_FMT))
    except FileNotFoundError:
        log.logger.warning("exiftool not found, cannot copy the creation date and geotagging of %s to %s", source, target)
    except Exception as e:
        log.logger.warning("Could not copy the creation date and geotagging of %s to %s: %s", source, target, e)


@contextlib.contextmanager
def preserve_dates(filename: str) -> Iterator[None]:
    """Keeps the dates of a file (creation, modification and access) when it is modified in place within the context"""
    try:
        stat = os.stat(filename)
    except OSError:
        yield
        return
    try:
        yield
    finally:
        restore_dates(filename, stat)


def restore_dates(filename: str, stat: os.stat_result) -> None:
    """Gives back to a file the dates (creation, modification and access) of a previous os.stat() of it. This never fails"""
    if not os.path.isfile(filename):
        return
    try:
        created = getattr(stat, "st_birthtime", stat.st_ctime)
        if abs(os.stat(filename).st_ctime - created) > 1 and os.name == "nt":
            # The creation date of a file can only be set with exiftool (the file system dates are set last as modifying the file changes them)
            with ExifToolHelper(executable=util.get_exiftool(), common_args=util.EXIFTOOL_ARGS, encoding="utf-8") as et:
                _set_tags(et, filename, {"File:FileCreateDate": datetime.fromtimestamp(created).strftime(util.EXIF_DATE_FMT)})
        os.utime(filename, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    except Exception as e:
        log.logger.warning("Could not keep the dates of %s: %s", filename, e)


def keeps_dates(func: Callable) -> Callable:
    """Decorator of the functions that modify in place the file given as first argument: the dates of the file are kept"""

    @functools.wraps(func)
    def wrapper(filename: str, *args: object, **kwargs: object) -> object:
        """Calls the function while keeping the dates of the file given as first argument"""
        with preserve_dates(filename):
            return func(filename, *args, **kwargs)

    return wrapper


def copy_after_ffmpeg(ffmpeg_params: str) -> None:
    """Copies the creation date and geotagging from the source to the file generated by an ffmpeg command, if any"""
    source, target = find_source_and_target(ffmpeg_params)
    if source is not None and target is not None:
        log.logger.debug("Copying the creation date and geotagging of %s to %s", source, target)
        copy_date_and_geotag(source, target)
