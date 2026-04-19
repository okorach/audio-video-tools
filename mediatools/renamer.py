#!python3
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

"""
This script renames files with format YYYY-MM-DD_HHMMSS_<root>
"""

from __future__ import annotations

import sys
import os
import argparse
import concurrent.futures
from exiftool import ExifToolHelper
import mediatools.utilities as util
import mediatools.log as log
import utilities.file as fil

SEQ: str = "#SEQ#"
SIZE: str = "#SIZE#"
DEVICE: str = "#DEVICE#"
TIMESTAMP: str = "#TIMESTAMP#"
FPS: str = "#FPS#"
BITRATE: str = "#BITRATE#"

DEFAULT_FORMAT: str = f"{util.FILE_DATE_FMT} - #SEQ3# - {SIZE} - {DEVICE}"
DEFAULT_VIDEO_FORMAT: str = f"{util.FILE_DATE_FMT} - {SEQ} - {SIZE} - {FPS}fps - {BITRATE}MBps"
DEFAULT_PHOTO_FORMAT: str = f"{util.FILE_DATE_FMT} - {SEQ} - {SIZE} - {DEVICE}"


def get_device(exif_data: dict[str, str]) -> str:
    device = ""
    if "EXIF:Make" in exif_data:
        device = exif_data["EXIF:Make"]
        if "EXIF:Model" in exif_data:
            device += " " + exif_data["EXIF:Model"]
    elif "QuickTime:Author" in exif_data:
        device = exif_data["QuickTime:Author"]
    elif "QuickTime:CompressorName" in exif_data:
        device = exif_data["QuickTime:CompressorName"]
    return device


def get_size(exif_data: dict[str, str]) -> str:
    size = ""
    if "File:ImageWidth" in exif_data and "File:ImageHeight" in exif_data:
        size = f'{exif_data["File:ImageWidth"]}x{exif_data["File:ImageHeight"]}'
    elif "EXIF:ExifImageWidth" in exif_data and "EXIF:ExifImageHeight" in exif_data:
        size = f'{exif_data["EXIF:ExifImageWidth"]}x{exif_data["EXIF:ExifImageHeight"]}'
    elif "QuickTime:SourceImageWidth" in exif_data and "QuickTime:SourceImageHeight" in exif_data:
        size = f'{exif_data["QuickTime:SourceImageWidth"]}x{exif_data["QuickTime:SourceImageHeight"]}'
    elif "QuickTime:ImageWidth" in exif_data and "QuickTime:ImageHeight" in exif_data:
        size = f'{exif_data["QuickTime:ImageWidth"]}x{exif_data["QuickTime:ImageHeight"]}'
    elif "Composite:ImageSize" in exif_data:
        size = exif_data["Composite:ImageSize"].replace(" ", "x")
    return size


def get_bitrate(exif_data: dict[str, str]) -> int | None:
    bitrate = None
    if "Composite:AvgBitrate" in exif_data:
        bitrate = round(int(exif_data["Composite:AvgBitrate"]) / 1024 / 1024)
    return bitrate


def get_codec(exif_data: dict[str, str]) -> str:
    codec = ""
    if "QuickTime:CompressorID" in exif_data:
        codec = exif_data["QuickTime:CompressorID"]

    if codec == "avc1":
        codec = "h264"
    elif codec == "hev1":
        codec = "h265"

    return codec


def get_fps(exif_data: dict[str, str]) -> int | None:
    fps = None
    if "QuickTime:VideoFrameRate" in exif_data:
        fps = round(float(exif_data["QuickTime:VideoFrameRate"]))
    return fps


def get_formats(nb_photos: int, nb_videos: int, **kwargs) -> tuple[str, str]:
    prefix = kwargs.get("prefix", None)
    pformat = vformat = SEQ
    if nb_videos > 0:
        if kwargs.get("video_format", None) in (None, ""):
            if prefix is None:
                print("Error: One of --prefix or --video_format option is required")
                sys.exit(1)
            vformat = f"{kwargs.get('prefix')} - {DEFAULT_VIDEO_FORMAT}"
        else:
            vformat = kwargs["video_format"]
    if nb_photos > 0:
        if kwargs.get("photo_format", None) in (None, ""):
            if prefix is None:
                print("Error: One of --prefix or --photo_format option is required")
                sys.exit(1)
            pformat = f"{kwargs.get('prefix')} - {DEFAULT_PHOTO_FORMAT}"
        else:
            pformat = kwargs["photo_format"]
    return (pformat, vformat)


def get_file_data(filename: str) -> dict | None:
    if fil.extension(filename).lower() not in fil.IMAGE_AND_VIDEO_EXTENSIONS:
        return None

    log.logger.info("Reading data for %s", filename)
    with ExifToolHelper() as et:
        for data in et.get_metadata(filename):
            log.logger.debug("MetaData = %s", util.json_fmt(data))
            creation_date = util.get_creation_date(data)
            device = get_device(data)
            bitrate = get_bitrate(data)
            fps = get_fps(data)
            size = get_size(data)
    return {
        "creation_date": creation_date,
        "device": device,
        "file": filename,
        "bitrate": bitrate,
        "size": size,
        "fps": fps,
    }


def get_files_data(files: list[str], sortby: str) -> dict:
    seq = 1
    filelist: dict = {}
    nb_files = len(files)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="GetMetadata") as executor:
        futures = [executor.submit(get_file_data, file) for file in files]
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result(timeout=10)  # Retrieve result or raise an exception
                log.logger.debug("Result: %s", str(result))
            except TimeoutError:
                log.logger.error("File renaming timed out after 60 seconds for %s, aborted.", str(future))
            except Exception as e:
                log.logger.error("File renaming task raised an exception: %s", str(e))
            if not result:
                continue
            if sortby == "name":
                filelist[result["filename"]] = result
            elif sortby == "device":
                if result["device"] is not None:
                    filelist[f"{result['device']} {seq:06}"] = result
            else:
                if result["creation_date"] is not None:
                    filelist[f"{result['creation_date'].strftime(util.FILE_DATE_FMT)} {seq:06}"] = result
            seq += 1
            log.logger.debug("Renamed %d/%d files = %d%%", seq, nb_files, (100 * seq) // nb_files)
    return filelist


def get_fmt(filename: str, photo_format: str, video_format: str, other_format: str) -> str:
    fmt = other_format
    if fil.is_image_file(filename):
        fmt = photo_format
    elif fil.is_video_file(filename):
        fmt = video_format
    if TIMESTAMP not in fmt and SEQ[:3] not in fmt:
        fmt = f"{SEQ} - {fmt}"
    return fmt


def rename(filename: str, new_filename: str, nbr_copies: int = 10) -> bool:
    if os.path.abspath(filename) == os.path.abspath(new_filename):
        log.logger.info("File %s needs no renaming", filename)
        return True
    log.logger.info("Renaming %s into %s", filename, new_filename)
    ext = fil.extension(new_filename)
    base = fil.strip_extension(filename)
    possible_files = [new_filename] + [f"{base} {v}.{ext}" for v in range(2, nbr_copies)]
    success = False
    for f in possible_files:
        try:
            os.rename(filename, f)
            success = True
            break
        except OSError as e:
            log.logger.info("Rename error: %s", str(e))
    if not success:
        log.logger.warning("Unable to rename")
        return False
    return True


def main() -> None:
    util.init("renamer")
    parser = argparse.ArgumentParser(description="Stacks images vertically or horizontally")
    parser.add_argument("-f", "--files", nargs="+", help="List of files to rename", required=True)
    parser.add_argument("--prefix", help="Prefix for files", required=False)
    parser.add_argument("--video_format", help="Format for the renamed video files", required=False)
    parser.add_argument("--format", help="Format for files", required=False, default=DEFAULT_FORMAT)
    parser.add_argument("--photo_format", help="Format for the renamed photo files", required=False)
    parser.add_argument("--seqstart", help="Sequence number start for the renamed files", required=False, default=1)
    parser.add_argument("-r", "--root", help="Root name", required=False)
    parser.add_argument("--sortby", help="How to sort sequence numbers", required=False, default="timestamp")
    parser.add_argument("-g", "--debug", required=False, type=int, help="Debug level")
    kwargs = util.parse_media_args(parser)

    file_list = fil.file_list(*kwargs["files"], file_type=None, recurse=False)
    nb_photo_files = sum(1 for f in file_list if fil.extension(f).lower() in fil.FileType.FILE_EXTENSIONS[fil.FileType.IMAGE_FILE])
    nb_video_files = sum(1 for f in file_list if fil.extension(f).lower() in fil.FileType.FILE_EXTENSIONS[fil.FileType.VIDEO_FILE])
    nb_other_files = len(file_list) - nb_photo_files - nb_video_files

    photo_seq = video_seq = other_seq = int(kwargs.get("seqstart", 1))
    (photo_format, video_format) = get_formats(nb_photo_files, nb_video_files, **kwargs)

    files_data = get_files_data(fil.file_list(*kwargs["files"], file_type=None, recurse=False), kwargs["sortby"])

    log.logger.info("%d image files and %d video files to process", nb_photo_files, nb_video_files)
    for key in sorted(files_data.keys()):
        filename = files_data[key]["file"]
        ext = fil.extension(filename).lower()
        device = files_data[key]["device"]
        creation_date = files_data[key]["creation_date"]
        fmt = get_fmt(filename, photo_format, video_format, kwargs["format"])
        file_fmt = fmt.replace(DEVICE, device)
        file_fmt = file_fmt.replace(TIMESTAMP, util.FILE_DATE_FMT)
        file_fmt = file_fmt.replace(BITRATE, str(files_data[key]["bitrate"]))
        file_fmt = file_fmt.replace(FPS, str(files_data[key]["fps"]))
        file_fmt = file_fmt.replace(SIZE, files_data[key]["size"])

        if fil.is_image_file(filename):
            seq = photo_seq
            nb_files = nb_photo_files
        elif fil.is_video_file(filename):
            seq = video_seq
            nb_files = nb_video_files
        else:
            seq = other_seq
            nb_files = nb_other_files
            log.logger.warning("%s is not a media file", filename)
        file_fmt = file_fmt.replace("#SEQ1#", f"{seq:01}")
        if nb_files < 100:
            file_fmt = file_fmt.replace(SEQ, f"{seq:02}")
        elif nb_files < 1000:
            file_fmt = file_fmt.replace(SEQ, f"{seq:03}")
        elif nb_files < 10000:
            file_fmt = file_fmt.replace(SEQ, f"{seq:04}")
        else:
            file_fmt = file_fmt.replace(SEQ, f"{seq:05}")
        file_fmt = file_fmt.replace("#SEQ2#", f"{seq:02}")
        file_fmt = file_fmt.replace("#SEQ3#", f"{seq:03}")
        file_fmt = file_fmt.replace("#SEQ4#", f"{seq:04}")
        file_fmt = file_fmt.replace("#SEQ5#", f"{seq:05}")
        new_filename = fil.dirname(filename) + os.sep + creation_date.strftime(file_fmt) + "." + ext
        file_type = fil.get_type(filename)
        if rename(filename, new_filename):
            if file_type == fil.FileType.IMAGE_FILE:
                photo_seq += 1
            elif file_type == fil.FileType.VIDEO_FILE:
                video_seq += 1
            else:
                other_seq += 1


if __name__ == "__main__":
    main()
