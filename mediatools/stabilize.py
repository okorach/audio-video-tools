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

# Two-pass video stabilization using libvidstab (vidstabdetect + vidstabtransform).
# Falls back to the simpler deshake filter when libvidstab is not compiled into FFmpeg.
# libvidstab is significantly more effective for action-cam footage because it analyses
# the full clip's motion trajectory before applying smoothing, whereas deshake works
# frame-by-frame with no global look-ahead.

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fil
from mediatools import log


def _has_vidstab() -> bool:
    """Return True if FFmpeg was compiled with libvidstab support."""
    try:
        quot = '"' if platform.system() == "Windows" else ""
        result = subprocess.run(
            [f"{quot}{util.get_ffmpeg()}{quot}", "-filters"],
            capture_output=True,
            text=True,
        )
        return "vidstabdetect" in result.stdout or "vidstabdetect" in result.stderr
    except Exception:
        return False


def stabilize(filename: str, output: str | None = None, shakiness: int = 8, smoothing: int = 30,
              zoom: int = 0, optzoom: int = 1, sharpen: bool = True, **kwargs) -> str:
    """Stabilize a video file using a two-pass libvidstab pipeline.

    Falls back to FFmpeg's deshake filter when libvidstab is not available.
    Returns the path of the stabilized output file.
    """
    output = util.automatic_output_file_name(infile=filename, outfile=output, postfix="stabilized")

    if not _has_vidstab():
        log.logger.warning("libvidstab not found in FFmpeg — falling back to deshake filter")
        kwargs["deshake"] = "32x32"
        kwargs["hw_accel"] = False  # deshake filter is CPU-only, incompatible with hwaccel
        return video.VideoFile(filename).encode(target_file=output, **kwargs)

    null_out = "NUL" if platform.system() == "Windows" else "/dev/null"

    with tempfile.NamedTemporaryFile(suffix=".trf", delete=False) as tf:
        trf_file = tf.name

    try:
        # Pass 1 — analyse motion and write the transforms file
        detect_vf = f"vidstabdetect=shakiness={shakiness}:accuracy=15:result='{trf_file}'"
        util.run_ffmpeg(f'-i "{filename}" -vf "{detect_vf}" -f null "{null_out}"')

        # Pass 2 — apply transforms; optionally sharpen to recover softness from interpolation
        transform_vf = f"vidstabtransform=smoothing={smoothing}:optzoom={optzoom}:zoom={zoom}:input='{trf_file}'"
        if sharpen:
            transform_vf += ",unsharp=5:5:0.8:3:3:0.4"
        util.run_ffmpeg(f'-i "{filename}" -vf "{transform_vf}" "{output}"')
    finally:
        if os.path.exists(trf_file):
            os.unlink(trf_file)

    return output


def main() -> None:
    parser = util.get_common_args("video-stabilize", "Stabilize shaky video footage (action cam, handheld) using two-pass libvidstab")
    parser.add_argument(
        "--shakiness",
        required=False,
        type=int,
        default=8,
        choices=range(1, 11),
        metavar="[1-10]",
        help="Shakiness level 1-10 (default 8, suitable for action cam footage)",
    )
    parser.add_argument(
        "--smoothing",
        required=False,
        type=int,
        default=30,
        help="Smoothing radius in frames — higher values produce steadier but more zoomed output (default 30)",
    )
    parser.add_argument(
        "--zoom",
        required=False,
        type=int,
        default=0,
        help="Additional zoom percentage to hide any residual black borders (default 0)",
    )
    parser.add_argument(
        "--optzoom",
        required=False,
        type=int,
        default=1,
        choices=[0, 1, 2],
        metavar="[0-2]",
        help="Auto-zoom mode: 0=none, 1=optimal zoom (default), 2=optimal zoom with panning",
    )
    parser.add_argument(
        "--no-sharpen",
        dest="sharpen",
        action="store_false",
        default=True,
        help="Skip the unsharp-mask pass applied after stabilization",
    )
    kwargs = util.parse_media_args(parser)

    input_files = fil.file_list(*kwargs["inputfiles"], file_type=fil.FileType.VIDEO_FILE)
    stab_kwargs = dict(
        shakiness=kwargs.get("shakiness", 8),
        smoothing=kwargs.get("smoothing", 30),
        zoom=kwargs.get("zoom", 0),
        optzoom=kwargs.get("optzoom", 1),
        sharpen=kwargs.get("sharpen", True),
    )
    # Only pass an explicit output path when processing a single file; for multiple
    # files (or a directory) each output is derived automatically from the input name.
    single = len(input_files) == 1
    for f in input_files:
        outputfile = stabilize(f, output=kwargs.get("outputfile") if single else None, **stab_kwargs)
        util.generated_file(outputfile)


if __name__ == "__main__":
    main()
