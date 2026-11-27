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
import re
import sys

import ffmpeg

import mediatools.exceptions as ex
import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fil
from mediatools import backups, log

DEFAULT_THRESHOLD: float = 2.0
DEFAULT_NORMALIZE_REPORT: str = "volume-normalize.csv"
CSV_HEADER: tuple[str, ...] = ("full_path", "mean_volume_db", "target_volume_db", "applied_gain_db", "backup_file")
# Name of the reports written by default, see _default_report()
_REPORT_NAME_RE: re.Pattern = re.compile(r"^volume-normalize(\.\d+)?\.csv$", re.IGNORECASE)
# ffmpeg encoder of each audio codec that can be re-encoded in the same codec (the pcm_* codecs are their own encoder)
_ENCODERS: dict[str, str] = {
    "mp3": "libmp3lame",
    "aac": "aac",
    "vorbis": "libvorbis",
    "opus": "libopus",
    "flac": "flac",
    "alac": "alac",
    "ac3": "ac3",
    "eac3": "eac3",
    "wmav2": "wmav2",
}
_LOSSLESS_CODECS: tuple[str, ...] = ("flac", "alac")


def _write_report(rows: list[list[object]], out_file: str) -> None:
    """Writes the CSV report of the files adjusted by _normalize_volume()"""
    with open(out_file, "w", newline="", encoding="utf-8") as fh:
        csv_writer = csv.writer(fh, dialect="excel", quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(CSV_HEADER)
        csv_writer.writerows(rows)
    util.generated_file(out_file)


def _free_name(filename: str, postfix: str, extension: str) -> str:
    """Returns <filename>.<postfix>.<extension>, with a sequence number after the postfix if that file already exists, so that no
    existing file is ever overwritten"""
    name = util.add_postfix(filename, postfix, extension)
    seq = 2
    while os.path.exists(name):
        name = util.add_postfix(filename, f"{postfix}.{seq}", extension)
        seq += 1
    return name


def _audio_encoding_options(filename: str) -> str:
    """Returns the ffmpeg options that re-encode the audio of a file in its own codec, at its own bitrate (lossy codecs) or sample
    format (lossless ones). Raises an InputError if that can't be done, rather than degrading the audio"""
    specs = ffmpeg.probe(filename, cmd=util.get_ffprobe())
    streams = specs.get("streams", [])
    stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if stream is None:
        raise ex.InputError(f"{filename} has no audio", "volume")
    codec = stream.get("codec_name", "")
    if codec.startswith("pcm_"):
        return f"-c:a {codec}"
    encoder = _ENCODERS.get(codec)
    if encoder is None:
        raise ex.InputError(f"Can't re-encode the {codec} audio of {filename} in the same codec", "volume")
    if codec in _LOSSLESS_CODECS:
        return f"-c:a {encoder} -sample_fmt {stream['sample_fmt']}"
    bitrate = stream.get("bit_rate")
    # The bitrate of the whole file is the one of the audio when there is no video (cover art apart)
    if not bitrate and all(s.get("codec_type") != "video" or s.get("disposition", {}).get("attached_pic") for s in streams):
        bitrate = specs.get("format", {}).get("bit_rate")
    if not bitrate:
        raise ex.InputError(f"Can't find the audio bitrate of {filename}", "volume")
    return f"-c:a {encoder} -b:a {bitrate}"


def _encode_with_volume(filename: str, gain: float, output: str) -> None:
    """Writes in output a copy of an audio or video file with its volume changed by gain dB. Only the audio is re-encoded (see
    _audio_encoding_options()), the video, cover art, subtitles and tags are copied"""
    options = _audio_encoding_options(filename)
    if fil.extension(output).lower() == "mp3":
        options += " -id3v2_version 3 -write_id3v1 1"
    util.run_ffmpeg(f'-i "{filename}" -map 0:v? -map 0:a -map 0:s? -map_metadata 0 -c copy {options} -filter:a "volume={gain:.2f}dB" "{output}"')


def _adjust_file(filename: str, mean_vol: float, average: float) -> list[object]:
    """Adjusts the volume of one file to the average, keeping the original as <filename>.before_volume.<ext>.
    Returns its CSV report row"""
    delta = average - mean_vol
    extension = fil.extension(filename)
    adjusted_file = _free_name(filename, "volume", extension)
    try:
        _encode_with_volume(filename, delta, adjusted_file)
    except Exception:
        if os.path.isfile(adjusted_file):
            os.remove(adjusted_file)
        raise
    before_file = backups.next_name(filename, backups.VOLUME)
    os.rename(filename, before_file)
    try:
        os.rename(adjusted_file, filename)
    except OSError:
        os.rename(before_file, filename)
        raise
    log.logger.info("%s: volume %.2f dB adjusted by %+.2f dB to reach the average, original kept as %s", filename, mean_vol, delta, before_file)
    util.generated_file(filename)
    return [os.path.abspath(filename), f"{mean_vol:.2f}", f"{average:.2f}", f"{delta:+.2f}", os.path.abspath(before_file)]


def _measure_volumes(files: list[str], progress: util.GlobalProgress) -> dict[str, float]:
    """Returns the mean volume of each file, leaving out (and logging) the ones that can't be measured"""
    mean_volumes: dict[str, float] = {}
    for f in files:
        try:
            mean_volumes[f] = video.get_mean_volume(f)
            log.logger.info("%s: mean volume %.2f dB", f, mean_volumes[f])
        except Exception as e:
            log.logger.error("Could not measure the volume of %s: %s", f, e)
        progress.done()
    return mean_volumes


def _normalize_volume(kwargs: dict) -> None:
    """Normalizes the volume of all the input files to their average mean volume, ignoring the backups of previous normalizations.
    Files whose mean volume is within options["threshold"] dB of the average are left unchanged.
    The others are adjusted in place: the original file is kept as <file>.before_volume.<ext>.
    Writes a CSV report of every modified file at -o (DEFAULT_NORMALIZE_REPORT by default), even if the run is interrupted.
    A file that fails is logged and skipped; the program then exits with code 1 at the end"""
    input_files = [f for f in kwargs[util.INPUT_FILES] if not backups.is_backup(f)]
    nb_backups = len(kwargs[util.INPUT_FILES]) - len(input_files)
    if nb_backups:
        log.logger.info("Ignoring %d backup file(s) of a previous normalization", nb_backups)
    threshold = kwargs.get("threshold", DEFAULT_THRESHOLD)
    out_file = kwargs.get(util.OUTPUT_FILE) or DEFAULT_NORMALIZE_REPORT

    progress = util.GlobalProgress(len(input_files) * 2)
    mean_volumes = _measure_volumes(input_files, progress)
    if not mean_volumes:
        log.logger.error("No file whose volume could be measured")
        sys.exit(1)
    average = sum(mean_volumes.values()) / len(mean_volumes)
    log.logger.info("Average volume across %d file(s): %.2f dB", len(mean_volumes), average)

    failed = len(input_files) - len(mean_volumes)
    rows: list[list[object]] = []
    try:
        for f in input_files:
            mean_vol = mean_volumes.get(f)
            if mean_vol is not None and abs(average - mean_vol) <= threshold:
                log.logger.info("%s: volume %.2f dB is within %.2f dB of the average, left unchanged", f, mean_vol, threshold)
            elif mean_vol is not None:
                try:
                    rows.append(_adjust_file(f, mean_vol, average))
                except Exception as e:
                    log.logger.error("Could not adjust the volume of %s: %s", f, e)
                    failed += 1
            progress.done()
    finally:
        _write_report(rows, out_file)
    log.logger.info("%d of %d file(s) adjusted, report written to %s", len(rows), len(input_files), out_file)
    if failed:
        log.logger.error("%d file(s) could not be processed", failed)
        sys.exit(1)


def _is_obsolete_report(report: str) -> bool:
    """Returns True if a file is a report of a normalization none of whose backups exists anymore"""
    try:
        with open(report, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
    except (OSError, UnicodeDecodeError, csv.Error):
        return False
    if not rows or tuple(rows[0]) != CSV_HEADER:
        return False
    backup_column = CSV_HEADER.index("backup_file")
    return not any(len(row) > backup_column and os.path.exists(row[backup_column]) for row in rows[1:])


def _remove_reports(inputs: list[str], out_file: str | None) -> None:
    """Removes the obsolete reports (see _is_obsolete_report()) named by default found in the input directories (recursively) and
    in the directories of the input files, and out_file if given and obsolete"""
    reports = {os.path.abspath(out_file)} if out_file else set()
    for path in inputs:
        path = os.path.abspath(path)
        folders = os.walk(path) if os.path.isdir(path) else [(os.path.dirname(path), [], None)]
        for folder, _, names in folders:
            if names is None:
                names = os.listdir(folder) if os.path.isdir(folder) else []
            reports.update(os.path.join(folder, name) for name in names if _REPORT_NAME_RE.match(name))
    for report in sorted(reports):
        if _is_obsolete_report(report):
            os.remove(report)
            log.logger.info("Removed the report %s", report)


def _restore_volume(inputs: list[str], out_file: str | None = None, audio_only: bool = False) -> None:
    """Undoes the normalizations of the inputs (see backups.restore()), then removes the reports that have become obsolete.
    The reports are kept, and the program exits with code 1, if a file can't be restored"""
    file_filter = (lambda f: fil.get_type(f) != fil.FileType.VIDEO_FILE) if audio_only else None
    backups.restore(inputs, backups.VOLUME, file_filter)
    _remove_reports(inputs, out_file)


def _default_report(first_input: str) -> str:
    """Returns the default report of a normalization: in the first input directory (or the directory of the first input file),
    without overwriting the report of a previous run"""
    folder = first_input if os.path.isdir(first_input) else os.path.dirname(os.path.abspath(first_input))
    stem, extension = DEFAULT_NORMALIZE_REPORT.rsplit(".", 1)
    name = os.path.join(folder, DEFAULT_NORMALIZE_REPORT)
    seq = 2
    while os.path.exists(name):
        name = os.path.join(folder, f"{stem}.{seq}.{extension}")
        seq += 1
    return name


def main() -> None:
    """Changes the volume of audio and video files, or normalizes it across many files"""
    parser = util.get_common_args("media-volume", "Change volume of a video or audio file, or normalize it across many files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--volume", help="Change volume like 400%% (relative change) or 6dB (absolute)")
    group.add_argument("--normalize", action="store_true", help="Normalize the volume of all input files to their average, see --threshold")
    backups.add_restore_arg(group)
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"With --normalize, max deviation in dB from the average volume left unchanged (default {DEFAULT_THRESHOLD})",
    )
    parser.add_argument("--audio_only", action="store_true", help="Only process the audio files, ignoring the videos")
    kwargs = util.parse_media_args(parser, expand_inputs=False)

    inputs = kwargs[util.INPUT_FILES]
    if kwargs.get("restore"):
        _restore_volume(inputs, kwargs.get(util.OUTPUT_FILE), bool(kwargs.get("audio_only")))
        return
    types = (fil.FileType.AUDIO_FILE,) if kwargs.get("audio_only") else (fil.FileType.VIDEO_FILE, fil.FileType.AUDIO_FILE)
    files = util.expand_input_files(inputs, types)
    if kwargs.get("audio_only"):
        files = [f for f in files if fil.get_type(f) == fil.FileType.AUDIO_FILE]
        if not files:
            log.logger.error("No audio file found in %s", ", ".join(inputs))
            sys.exit(1)
    kwargs[util.INPUT_FILES] = files

    if kwargs.get("normalize"):
        kwargs.setdefault(util.OUTPUT_FILE, _default_report(inputs[0]))
        _normalize_volume(kwargs)
        return

    def process(input_file: str, options: dict) -> None:
        """Changes the volume of one audio or video file"""
        util.generated_file(video.volume(input_file, options["volume"]))

    util.process_input_files(kwargs, process)


if __name__ == "__main__":
    main()
