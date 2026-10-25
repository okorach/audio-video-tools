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

# This script applies a configurable before/after ffmpeg command to one or more video files.
# Accepts a single file or a directory (all video files in the directory are processed).

"""Tool that encodes video files automatically with the ffmpeg options given"""

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


def main() -> None:
    """Encodes video files automatically with the ffmpeg options given, replacing the originals, and logs the global progress"""
    parser = argparse.ArgumentParser(description="Simple encoder — accepts a file or directory")
    util.add_input_args(parser, "Video files and/or directories to encode")
    util.add_verbosity_arg(parser)
    parser.add_argument("--nooverwrite", required=False, default=False, action="store_true")
    parser.add_argument("--keepName", required=False, default=False, action="store_true")
    parser.add_argument("--before", nargs="*", required=True)
    parser.add_argument("--after", nargs="*", required=True)
    kwargs = vars(parser.parse_args())
    util.set_debug_level(util.get_verbosity(kwargs))

    inputpath = ", ".join(kwargs[util.INPUT_FILES])
    before = " ".join(kwargs["before"])
    after = " ".join(kwargs["after"])
    force = not kwargs["nooverwrite"]

    files = [f for f in fileutil.expand_inputs(kwargs[util.INPUT_FILES], fileutil.FileType.VIDEO_FILE) if fileutil.is_video_file(f)]
    if not files:
        logger.error("No video files found in %s", inputpath)
        return

    n = len(files)
    durations = [video.get_duration(f) or 0.0 for f in files]
    total_dur = sum(durations)
    logger.info("%d file(s) to encode, total duration: %s", n, util.to_hms_str(total_dur))

    processed_dur = 0.0
    wall_start = time.time()

    for i, (f, dur) in enumerate(zip(files, durations, strict=True)):
        encode_file(f, before, after, force, duration=total_dur - processed_dur)
        processed_dur += dur
        pct = 100.0 * processed_dur / total_dur if total_dur > 0 else 100.0
        elapsed = time.time() - wall_start
        speed = processed_dur / elapsed if elapsed > 0 else 0
        eta = (total_dur - processed_dur) / speed if speed > 0 else 0
        logger.info("Processed %d/%d - %.0f%% - ETA %s", i + 1, n, pct, util.to_hms_str(eta))


if __name__ == "__main__":
    main()
