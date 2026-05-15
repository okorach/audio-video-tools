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

"""Accelerates or slows down an audio file using the atempo filter."""

import sys
import mediatools.utilities as util
import mediatools.audiofile as audio
from mediatools import log


def _atempo_filters(factor: float) -> list[str]:
    """Returns a chained list of atempo filter strings whose product equals factor.
    atempo only accepts values in [0.5, 2.0], so multiple filters are chained when needed."""
    parts = []
    remaining = factor
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining *= 2.0
    parts.append(f"atempo={remaining:.6f}")
    return parts


def speed(input_file: str, output_file: str | None, size_percent: float) -> str:
    """Changes the tempo of an audio file.

    size_percent is the target duration expressed as a percentage of the original:
      < 100  →  file is shorter  →  playback is faster  (e.g. 90 = 10% faster)
      > 100  →  file is longer   →  playback is slower  (e.g. 110 = 10% slower)
    """
    factor = 100.0 / size_percent
    af = audio.AudioFile(input_file)
    af.get_specs()
    af_filter = ",".join(_atempo_filters(factor))
    output_file = util.automatic_output_file_name(output_file, input_file, f"speed{size_percent:.0f}")
    log.logger.info("Changing speed of %s: size=%g%% → atempo factor=%.4f", input_file, size_percent, factor)
    bitrate_opt = f'-b:a "{af.abitrate}"' if af.abitrate else ""
    duration = (af.duration / factor) if af.duration else None
    cmd = f'-i "{input_file}" -af "{af_filter}" {bitrate_opt} "{output_file}"'
    util.run_ffmpeg(cmd.strip(), duration)
    return output_file


def main():
    parser = util.get_common_args("audio-speed", "Accelerates or slows down an audio file")
    parser.add_argument(
        "--size",
        required=True,
        type=float,
        help="Target duration as %% of original (e.g. 90 = 10%% faster, 110 = 10%% slower)",
    )
    kwargs = util.parse_media_args(parser)
    size_percent = kwargs["size"]
    if size_percent <= 0:
        log.logger.error("--size must be a positive number, got %g", size_percent)
        sys.exit(1)
    input_file = kwargs["inputfiles"][0]
    output = speed(input_file, kwargs.get("outputfile"), size_percent)
    util.generated_file(output)


if __name__ == "__main__":
    main()
