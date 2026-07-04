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

"""Enhances video colors to produce more vivid, punchy images using the ffmpeg eq filter."""

import os
import time
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.stabilize as stab
import utilities.file as fileutil
from mediatools import log


def enhance_file(
    input_file: str,
    output_file: str | None,
    saturation: float,
    contrast: float,
    brightness: float,
    gamma: float,
    hw_accel: bool | None = None,
    stabilize: bool = True,
    batch_remaining: float | None = None,
) -> None:
    """Color-enhance a single video file, preserve creation date, rename original."""
    creation_date = video.get_creation_date(input_file)
    extra = {} if hw_accel is None else {"hw_accel": hw_accel}
    if batch_remaining is not None:
        extra["batch_remaining"] = batch_remaining

    trf_file = None
    if stabilize:
        if stab.has_vidstab():
            try:
                trf_file = stab.run_vidstabdetect(input_file)
                extra["vidstab_trf"] = trf_file
            except Exception as e:
                log.logger.warning("vidstabdetect failed for %s, skipping stabilization: %s", input_file, e)
        else:
            log.logger.warning("libvidstab not available — falling back to deshake filter")
            extra["deshake"] = "32x32"

    try:
        outfile = video.color_enhance(input_file, output_file, saturation=saturation, contrast=contrast, brightness=brightness, gamma=gamma, **extra)
    except Exception as e:
        log.logger.error("Failed to enhance %s: %s", input_file, e)
        return
    finally:
        if trf_file and os.path.exists(trf_file):
            os.unlink(trf_file)
    video.set_creation_date(outfile, creation_date)

    if output_file is None:
        base, ext = os.path.splitext(input_file)
        fileutil.rename(input_file, f"{base}.original{ext}")
        fileutil.rename(outfile, input_file)
        util.generated_file(input_file)
    else:
        util.generated_file(outfile)


def main():
    parser = util.get_common_args("video-enhance", "Enhance video colors (saturation, contrast, brightness, gamma)")
    parser.add_argument(
        "--saturation", required=False, type=float, default=1.3, help="Color saturation multiplier (default 1.3, neutral 1.0, range 0-3)"
    )
    parser.add_argument("--contrast", required=False, type=float, default=1.1, help="Contrast multiplier (default 1.1, neutral 1.0, range -2 to 2)")
    parser.add_argument("--brightness", required=False, type=float, default=0.0, help="Brightness offset (default 0.0, range -1 to 1)")
    parser.add_argument("--gamma", required=False, type=float, default=1.0, help="Gamma correction (default 1.0, range 0.1 to 10)")
    parser.add_argument(
        "--gpu_filters",
        required=False,
        default=False,
        action="store_true",
        help="Use GPU hw acceleration with GPU-compatible filters only (disables eq color filter)",
    )
    parser.add_argument(
        "--no_stabilize", required=False, default=False, action="store_true", help="Skip video stabilization (stabilization is applied by default)"
    )
    kwargs = util.parse_media_args(parser)

    output_file = kwargs.get("outputfile", None)
    saturation = kwargs["saturation"]
    contrast = kwargs["contrast"]
    brightness = kwargs["brightness"]
    gamma = kwargs["gamma"]
    hw_accel = None if kwargs.get("gpu_filters", False) else False
    do_stabilize = not kwargs.get("no_stabilize", False)

    all_files = fileutil.file_list(*kwargs["inputfiles"], file_type=fileutil.FileType.VIDEO_FILE, recurse=True)
    files = [f for f in all_files if ".color." not in os.path.basename(f) and ".original." not in os.path.basename(f)]
    if len(files) < len(all_files):
        log.logger.info("Skipped %d already-generated file(s) (.color./.original.)", len(all_files) - len(files))
    if not files:
        log.logger.error("No video files found in %s", kwargs["inputfiles"])
        return

    if output_file is not None and len(files) > 1:
        log.logger.error("-o/--outputfile cannot be used with multiple input files; omit it to rename in place")
        return

    n = len(files)
    durations = [video.get_duration(f) or 0.0 for f in files]
    total_dur = sum(durations)
    log.logger.info("%d file(s) to enhance, total duration: %s", n, util.to_hms_str(total_dur))

    processed_dur = 0.0
    wall_start = time.time()

    for i, (f, dur) in enumerate(zip(files, durations)):
        enhance_file(
            f,
            output_file,
            saturation,
            contrast,
            brightness,
            gamma,
            hw_accel=hw_accel,
            stabilize=do_stabilize,
            batch_remaining=total_dur - processed_dur,
        )
        processed_dur += dur
        pct = 100.0 * processed_dur / total_dur if total_dur > 0 else 100.0
        elapsed = time.time() - wall_start
        speed = processed_dur / elapsed if elapsed > 0 else 0
        eta = (total_dur - processed_dur) / speed if speed > 0 else 0
        log.logger.info("Processed %d/%d - %.0f%% - ETA %s", i + 1, n, pct, util.to_hms_str(eta))


if __name__ == "__main__":
    main()
