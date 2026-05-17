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

# This script applies a configurable before/after ffmpeg command to one or more video files.
# Accepts a single file or a directory (all video files in the directory are processed).

import os
import time
import argparse
from mediatools.log import logger
import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fileutil


def encode_file(inputfile: str, before: str, after: str, force: bool, duration: float | None = None) -> None:
    """Encode a single video file with the given before/after ffmpeg options."""
    base, ext = os.path.splitext(inputfile)
    ext = ext.lstrip(".").lower()

    is_original = base.endswith(".original")
    if is_original:
        base = base[: -len(".original")]

    file_after = after
    new_ext = ext
    if ext in ("mts", "avi", "mkv"):
        file_after = f"-vf yadif_cuda=deint=all {after}"
        new_ext = "mp4"

    logger.info("Encoding %s (ext=%s)", inputfile, ext)
    seq = 0
    if not force:
        while os.path.isfile(f"{base}.encode.{seq:02}.{new_ext}"):
            seq += 1
    outputfile = f"{base}.encode.{seq:02}.{new_ext}"

    cmd = f'{before} -i "{inputfile}" {file_after} "{outputfile}"'
    logger.info("COMMAND = ffmpeg %s", cmd)
    if duration is None:
        duration = video.get_duration(inputfile)
    util.run_ffmpeg(params=cmd, duration=duration)

    video.set_creation_date(outputfile, video.get_creation_date(inputfile))
    if ext == new_ext:
        if not is_original:
            renamed = f"{base}.original.{ext}"
            fileutil.rename(inputfile, renamed, force)
            fileutil.rename(outputfile, inputfile, force)
        else:
            os.rename(outputfile, f"{base}.{ext}")
    else:
        fileutil.rename(outputfile, f"{base}.{new_ext}", force)


def main():
    parser = argparse.ArgumentParser(description="Simple encoder — accepts a file or directory")
    parser.add_argument("-i", "--inputfiles", type=str, required=True)
    parser.add_argument("-g", "--debug", required=False)
    parser.add_argument("--nooverwrite", required=False, default=False, action="store_true")
    parser.add_argument("--keepName", required=False, default=False, action="store_true")
    parser.add_argument("--before", nargs="*", required=True)
    parser.add_argument("--after", nargs="*", required=True)
    kwargs = vars(parser.parse_args())
    util.set_debug_level(kwargs.get("debug", 3))

    inputpath = kwargs["inputfiles"]
    before = " ".join(kwargs["before"])
    after = " ".join(kwargs["after"])
    force = not kwargs["nooverwrite"]

    files = fileutil.file_list(inputpath, file_type=fileutil.FileType.VIDEO_FILE)
    if not files:
        logger.error("No video files found in %s", inputpath)
        return

    n = len(files)
    durations = [video.get_duration(f) or 0.0 for f in files]
    total_dur = sum(durations)
    logger.info("%d file(s) to encode, total duration: %s", n, util.to_hms_str(total_dur))

    processed_dur = 0.0
    wall_start = time.monotonic()

    for i, (f, dur) in enumerate(zip(files, durations)):
        encode_file(f, before, after, force, duration=dur)
        processed_dur += dur
        wall_elapsed = time.monotonic() - wall_start
        remaining_dur = total_dur - processed_dur
        speed = processed_dur / wall_elapsed if wall_elapsed > 0 else 0.0
        eta = util.to_hms_str(remaining_dur / speed) if speed > 0 else "unknown"
        logger.info(
            "Progress: %d/%d files | %s / %s encoded (%.0f%%) | Speed: %.2fx | ETA: %s",
            i + 1, n,
            util.to_hms_str(processed_dur),
            util.to_hms_str(total_dur),
            100.0 * processed_dur / total_dur if total_dur > 0 else 100.0,
            speed,
            eta,
        )


if __name__ == "__main__":
    main()
