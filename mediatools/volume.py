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

"""This script changes the volume of a video or audio file, or normalizes it across many files"""

import csv
import os

import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fil
from mediatools import log

DEFAULT_THRESHOLD: float = 2.0
DEFAULT_NORMALIZE_REPORT: str = "volume-normalize.csv"
CSV_HEADER: tuple[str, ...] = ("full_path", "mean_volume_db", "target_volume_db", "applied_gain_db", "backup_file")


def _write_report(rows: list[list[object]], out_file: str) -> None:
    """Writes the CSV report of the files adjusted by _normalize_volume()"""
    with open(out_file, "w", newline="", encoding="utf-8") as fh:
        csv_writer = csv.writer(fh, dialect="excel", quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(CSV_HEADER)
        csv_writer.writerows(rows)
    util.generated_file(out_file)


def _adjust_file(filename: str, mean_vol: float, average: float) -> list[object]:
    """Adjusts the volume of one file to the average, keeping the original as <filename>.before_volume.<ext>.
    Returns its CSV report row"""
    delta = average - mean_vol
    before_file = util.add_postfix(filename, "before_volume", fil.extension(filename))
    adjusted_file = video.volume(filename, f"{delta:.2f}dB")
    fil.rename(filename, before_file)
    fil.rename(adjusted_file, filename)
    log.logger.info("%s: volume %.2f dB adjusted by %+.2f dB to reach the average, original kept as %s", filename, mean_vol, delta, before_file)
    util.generated_file(filename)
    return [os.path.abspath(filename), f"{mean_vol:.2f}", f"{average:.2f}", f"{delta:+.2f}", os.path.abspath(before_file)]


def _normalize_volume(kwargs: dict) -> None:
    """Normalizes the volume of all the input files to their average mean volume.
    Files whose mean volume is within options["threshold"] dB of the average are left unchanged.
    The others are adjusted in place: the original file is kept as <file>.before_volume.<ext>.
    Writes a CSV report of every modified file at -o (DEFAULT_NORMALIZE_REPORT by default)"""
    input_files = kwargs[util.INPUT_FILES]
    threshold = kwargs.get("threshold", DEFAULT_THRESHOLD)
    out_file = kwargs.get(util.OUTPUT_FILE) or DEFAULT_NORMALIZE_REPORT

    progress = util.GlobalProgress(len(input_files) * 2)
    mean_volumes: dict[str, float] = {}
    for f in input_files:
        mean_volumes[f] = video.get_mean_volume(f)
        log.logger.info("%s: mean volume %.2f dB", f, mean_volumes[f])
        progress.done()

    average = sum(mean_volumes.values()) / len(mean_volumes)
    log.logger.info("Average volume across %d file(s): %.2f dB", len(mean_volumes), average)

    rows: list[list[object]] = []
    for f, mean_vol in mean_volumes.items():
        if abs(average - mean_vol) <= threshold:
            log.logger.info("%s: volume %.2f dB is within %.2f dB of the average, left unchanged", f, mean_vol, threshold)
        else:
            rows.append(_adjust_file(f, mean_vol, average))
        progress.done()

    _write_report(rows, out_file)
    log.logger.info("%d of %d file(s) adjusted, report written to %s", len(rows), len(input_files), out_file)


def main() -> None:
    """Changes the volume of audio and video files, or normalizes it across many files"""
    parser = util.get_common_args("media-volume", "Change volume of a video or audio file, or normalize it across many files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--volume", help="Change volume like 400%% (relative change) or 6dB (absolute)")
    group.add_argument("--normalize", action="store_true", help="Normalize the volume of all input files to their average, see --threshold")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"With --normalize, max deviation in dB from the average volume left unchanged (default {DEFAULT_THRESHOLD})",
    )
    kwargs = util.parse_media_args(parser, input_type=(fil.FileType.VIDEO_FILE, fil.FileType.AUDIO_FILE))

    if kwargs.get("normalize"):
        _normalize_volume(kwargs)
        return

    def process(input_file: str, options: dict) -> None:
        """Changes the volume of one audio or video file"""
        util.generated_file(video.volume(input_file, options["volume"]))

    util.process_input_files(kwargs, process)


if __name__ == "__main__":
    main()
