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

"""Utilities shared by the tools: ffmpeg execution, logs, command line arguments, hardware acceleration, progress..."""

import argparse
import contextvars
import functools
import inspect
import json
import logging
import os
import pathlib
import platform
import re
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable
from datetime import datetime

import mediatools.media_config as conf
import mediatools.options as opt
import mediatools.resolution as res
import utilities.file as fil
from mediatools import log, metacopy, version

DEBUG_LEVEL: int = 0

# Names of the input and output files options (--inputfiles/--outputfile) and of the corresponding keys of the parsed arguments
INPUT_FILES: str = "inputfiles"
OUTPUT_FILE: str = "outputfile"
DRY_RUN: bool = False
# Result of the check of the availability of the hardware acceleration (None = not checked yet)
HW_ACCEL: bool | None = None
HW_ACCEL_PREFIX: str = "-hwaccel cuda -hwaccel_output_format cuda"
HW_ACCEL_MODES: tuple[str, ...] = ("auto", "on", "off")
# A command line using one of those options (or an nvenc/cuvid/cuda codec or filter) is a hardware accelerated command
HW_ACCEL_COMMAND_REGEXP: re.Pattern = re.compile(r"-hwaccel|_nvenc|_cuvid|_cuda|_qsv|_amf")

# State of the fallback of the hardware acceleration (context variables, so that it's safe with threads)
_hw_attempt_depth: contextvars.ContextVar[int] = contextvars.ContextVar("hw_attempt_depth", default=0)
_hw_forced_off: contextvars.ContextVar[bool] = contextvars.ContextVar("hw_forced_off", default=False)
_hw_command_run: contextvars.ContextVar[list | None] = contextvars.ContextVar("hw_command_run", default=None)

LANGUAGE_MAPPING: dict[str, str] = {"fre": "French", "eng": "English"}

OPTIONS_VERBATIM: list[str] = ["ss", "to"]

FILE_DATE_FMT: str = "%Y-%m-%d %Hh%Mm%Ss"
ISO_DATE_FMT: str = "%Y-%m-%d %H:%M:%S"
EXIF_DATE_FMT: str = "%Y:%m:%d %H:%M:%S"
DATE_FORMATS: tuple[str, ...] = (ISO_DATE_FMT, f"{ISO_DATE_FMT}%z", EXIF_DATE_FMT, f"{EXIF_DATE_FMT}%z")
CREATION_DATE_TAGS: tuple[str, ...] = ("QuickTime:CreateDate", "EXIF:DateTimeOriginal", "File:FileModifyDate", "File:FileCreateDate")

config_props = os.path.realpath(__file__).split(os.path.sep)
config_props.pop()
config_props.pop()
config_props.append("media-tools.properties")
DEFAULT_PROPERTIES_FILE: str = os.path.sep.join(config_props)

PROPERTIES_FILE: str = ""
PROPERTIES_VALUES: dict = {}


def add_postfix(file: str, postfix: str, extension: str | None = None) -> str:
    """Adds a postfix to a file before the file extension"""
    if extension is None:
        extension = conf.get_property(f"default.{fil.get_type(file)}.format")
    if extension is None:
        extension = fil.extension(file)
    return fil.strip_extension(file) + r"." + postfix + r"." + extension


def automatic_output_file_name(outfile: str | None, infile: str, postfix: str, extension: str | None = None) -> str:
    """Returns the output file name: the given one if there is one, otherwise the name of the input file with a postfix and an extension"""
    if outfile is not None:
        return outfile
    postfix = postfix.replace(":", "-")
    return add_postfix(infile, postfix, extension)


def get_ffbin(ffprop: str) -> str:
    """Returns the path of an ffmpeg binary (ffmpeg, ffprobe) from its property of the configuration file"""
    props = get_media_properties()

    if not re.search("\\" + os.path.sep, props[ffprop]):
        return props[ffprop]
    return props[ffprop]  # os.path.realpath(props[ffprop])


def get_ffmpeg() -> str:
    """Returns the path of ffmpeg"""
    return get_ffbin("binaries.ffmpeg")


def get_ffprobe() -> str:
    """Returns the path of ffprobe"""
    return get_ffbin("binaries.ffprobe")


def get_exiftool() -> str:
    """Returns the path of exiftool"""
    return get_media_properties().get("binaries.exiftool", "exiftool")


def get_first_value(a_dict: dict | None, key_list: tuple | list) -> object | None:
    """Returns the value of the first of the keys that is in a dictionary, None if there is none"""
    if a_dict is None:
        return None
    for tag in key_list:
        if tag in a_dict:
            return a_dict[tag]
    return None


# The progress line of ffmpeg: "size=... time=<hh:mm:ss.ms> bitrate=... speed=<speed>x"
FFMPEG_TIME_RE: re.Pattern = re.compile(r" time=(\d+:\d+:\d+\.\d+)\s+bitrate=")
FFMPEG_SPEED_RE: re.Pattern = re.compile(r"speed=\s*(\d+(?:\.\d*)?|\.\d+)x")


def __compute_eta__(line: str, total_time: float | str | None) -> str:
    """Returns the progress and the ETA of an ffmpeg progress line. With several files, the progress of the file and the global progress are returned
    Returns the progress and the ETA of an ffmpeg progress line. With several files, the progress of the file and the global progress are returned"""
    if total_time is None:
        return ""
    time_match = FFMPEG_TIME_RE.search(line) if "size=" in line else None
    speed_match = FFMPEG_SPEED_RE.search(line, time_match.end()) if time_match else None
    if not time_match or not speed_match:
        log.logger.debug("%s does not match the progress line of ffmpeg", line)
        return ""
    speed = float(speed_match.group(1))
    done_time = to_seconds(time_match.group(1))
    eta = "Undefined" if speed == 0 else to_hms_str(max(0, (total_time - done_time) / speed))
    progress = GlobalProgress.current
    if progress is None or total_time <= 0:
        return f" ETA={eta}"
    # Several files are processed: display the progress of the file and the global progress
    file_fraction = min(max(done_time / total_time, 0.0), 1.0)
    return f" - File progress {file_fraction * 100:.0f}%/ETA {eta} - {progress.status(file_fraction)}"


def __get_log_level_from_ffmpeg_log__(line: str) -> int:
    """Returns the log level (error, info, warning or debug) of a line of the ffmpeg output"""
    if re.search(r"Picture size \d+x\d+ is invalid", line, re.IGNORECASE):
        level = logging.WARNING
    elif re.search(r"(error|invalid|failed)", line, re.IGNORECASE):
        level = logging.ERROR
    elif re.search(r"frame=\s*\d+\s+fps=\s*\d+", line, re.IGNORECASE):
        level = logging.INFO
    elif re.search(r"(warning|deprecated|out of range)", line, re.IGNORECASE):
        level = logging.WARNING
    else:
        level = logging.DEBUG
    return level


def run_os_cmd(cmd: str, total_time: float | str | None = None) -> None:
    """Runs a command and logs its output. The ETA is logged for the ffmpeg commands when the total time of the output is known. Raises a
    CalledProcessError if the command fails"""
    log.logger.info("Running: %s", cmd)
    if total_time is not None and isinstance(total_time, str):
        total_time = to_seconds(total_time)
    try:
        last_seen_line, last_seen_level, same_line_count = None, logging.INFO, 0
        last_error_line = None
        args = shlex.split(cmd)
        pipe = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding="utf-8", errors="replace", bufsize=1
        )
        line = pipe.stdout.readline().rstrip()
        while line:
            level = __get_log_level_from_ffmpeg_log__(line)
            line += __compute_eta__(line, total_time)
            if level >= logging.ERROR:
                log.logger.log(level, line)
                last_error_line = line
                last_seen_line = None
                same_line_count = 0
            elif last_seen_line is not None and last_seen_line == line:
                same_line_count += 1
            else:
                if same_line_count > 1:
                    log.logger.log(last_seen_level, "Above line repeated %d times", same_line_count)
                log.logger.log(level, line)
                same_line_count = 1
                last_seen_line = line
                last_seen_level = level
            line = pipe.stdout.readline().rstrip()
        pipe.communicate()
        log.logger.debug("Return code = %d", pipe.returncode)
        if pipe.returncode not in (0, 3221225477):  # TODO: Better than this ugly hack for ffmpeg
            raise subprocess.CalledProcessError(cmd=cmd, output=last_error_line or last_seen_line, returncode=pipe.returncode)
        log.logger.info("Successfully completed: %s", cmd)
    except subprocess.CalledProcessError as e:
        log.logger.error("Command: %s failed with return code %d", cmd, e.returncode)
        if e.output:
            log.logger.error("Last ffmpeg error: %s", e.output)
        raise e


def run_ffmpeg(params: str, duration: float | None = None) -> None:
    """Runs ffmpeg with some parameters, then copies the date and the geotagging of the source file to the generated file"""
    commands = _hw_command_run.get()
    if commands is not None and HW_ACCEL_COMMAND_REGEXP.search(params):
        commands.append(params)  # Remember that a hardware accelerated command was run, see hw_accel_fallback()
    quot = '"' if platform.system() == "Windows" else ""
    cmd = f"{quot}{get_ffmpeg()}{quot} -y -stats_period {FFMPEG_STATS_PERIOD} {params}"
    run_os_cmd(cmd, duration)
    metacopy.copy_after_ffmpeg(params)


def build_ffmpeg_complex_prep(input_file_list: list) -> str:
    """Returns the filter graph that rescales the inputs [0] to [n] with the lanczos algorithm, as the streams [pip0] to [pipN]"""
    s = ""
    for i in range(len(input_file_list) + 1):
        s += f"[{i}]scale=iw:-1:flags=lanczos[pip{i}]; "
    return s


def get_media_properties() -> dict:
    """Returns all properties found in the properties file as dictionary"""
    global PROPERTIES_VALUES
    if not PROPERTIES_VALUES:
        PROPERTIES_VALUES = conf.load()
        log.logger.debug("Props = %s", json_fmt(PROPERTIES_VALUES))
    return PROPERTIES_VALUES


def get_conf_property(prop: str) -> str | int | float | bool | None:
    """Returns a property of the configuration file, loading the configuration if needed"""
    if not PROPERTIES_VALUES:
        get_media_properties()
    return PROPERTIES_VALUES[prop]


def to_hms(seconds: float | str, fmt: str = "tuple") -> tuple[int, int, float] | str:
    """Converts a number of seconds to hours, minutes and seconds: a tuple, or a string hh:mm:ss.sss if fmt is 'string'"""
    try:
        s = int(float(seconds))
        hours = s // 3600
        minutes = s // 60 - hours * 60
        secs = round(float(seconds) - hours * 3600 - minutes * 60, 3)
        if fmt == "string":
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        return (hours, minutes, secs)
    except (TypeError, ValueError):
        if fmt == "string":
            return "00:00:00"
        return (0, 0, 0)


def to_seconds(hms: float | str) -> float:
    """Converts a duration in the form [hh:]mm:ss.sss, or a number of seconds, to a number of seconds"""
    a = [float(x) for x in str(hms).split(":")]
    if len(a) == 3:
        return a[0] * 3600 + a[1] * 60 + a[2]
    if len(a) == 2:
        return a[0] * 60 + a[1]
    return a[0]


def difftime(stop: float | str, start: float | str) -> float:
    """Returns the number of seconds between 2 times"""
    return to_seconds(stop) - to_seconds(start)


def to_hms_str(seconds: float) -> str:
    """Converts a number of seconds to a string hh:mm:ss.sss"""
    hours, minutes, secs = to_hms(seconds)
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def json_fmt(json_data: object) -> str:
    """Returns a data structure as a readable JSON string"""
    return json.dumps(json_data, sort_keys=True, indent=3, separators=(",", ": "))


VERBOSITY_LEVELS: tuple[str, ...] = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")  # Index = integer debug level
DEFAULT_VERBOSITY = "INFO"


def parse_verbosity(level: int | str | None) -> int:
    """Converts a verbosity (CRITICAL, ERROR, WARNING, INFO, DEBUG - case insensitive, or the equivalent integer 0 to 4) to its integer level.
    INFO (3) is the default"""
    if level is None or str(level).strip() == "":
        return VERBOSITY_LEVELS.index(DEFAULT_VERBOSITY)
    text = str(level).strip().upper()
    if text in VERBOSITY_LEVELS:
        return VERBOSITY_LEVELS.index(text)
    return int(text)


def get_verbosity(kwargs: dict) -> int:
    """Returns the integer verbosity level from the parsed arguments (-v/--verbosity, or the deprecated -g/--debug)"""
    return parse_verbosity(kwargs.get("verbosity") or kwargs.get("debug"))


def add_verbosity_arg(parser: argparse.ArgumentParser) -> None:
    """Adds the -v/--verbosity option to the parser of a tool (and the deprecated -g/--debug alias, that accepts the same values)"""
    parser.add_argument(
        "-v",
        "--verbosity",
        required=False,
        metavar="|".join(VERBOSITY_LEVELS),
        type=str.upper,
        choices=VERBOSITY_LEVELS,
        help=f"Verbosity of the logs, {DEFAULT_VERBOSITY} by default",
    )
    parser.add_argument("-g", "--debug", required=False, help=argparse.SUPPRESS)


def set_debug_level(level: int | str | None) -> None:
    """Sets the verbosity of the logs: CRITICAL, ERROR, WARNING, INFO (default) or DEBUG, or the equivalent integer from 0 to 4"""
    global DEBUG_LEVEL
    DEBUG_LEVEL = parse_verbosity(level)
    log.logger.setLevel(log.get_logging_level(DEBUG_LEVEL))
    log.logger.info("Set verbosity to %s", VERBOSITY_LEVELS[min(max(DEBUG_LEVEL, 0), 4)])


def init(logger_name: str) -> None:
    """Initializes the logs of a tool: they are written in the console and in the file <logger_name>.log"""
    log.set_logger(logger_name)
    log.logger.setLevel(log.get_logging_level(3))
    log.logger.info("audio-video-tools version %s", version.MEDIA_TOOLS_VERSION)


def delete_files(*args: str) -> None:
    """Deletes files"""
    for f in args:
        log.logger.debug("Deleting file %s", f)
        os.remove(f)


def add_input_args(
    parser: argparse.ArgumentParser,
    help_text: str = "List of files to process",
    required: bool = True,
    dest: str = INPUT_FILES,
    aliases: tuple[str, ...] = (),
) -> None:
    """Adds the -i/--inputfiles option (files and/or directories) to the parser of a tool.
    aliases are other (deprecated) names of the option, dest is the name of the parsed argument"""
    parser.add_argument("-i", "--" + INPUT_FILES, *aliases, dest=dest, required=required, nargs="+", help=help_text)


def add_output_args(parser: argparse.ArgumentParser, help_text: str = "Output file or directory", required: bool = False) -> None:
    """Adds the -o/--outputfile option to the parser of a tool"""
    parser.add_argument("-o", "--" + OUTPUT_FILE, required=required, help=help_text)


def get_common_args(executable: str, desc: str, inputs_required: bool = True) -> argparse.ArgumentParser:
    """Parses options common to all media encoding scripts"""
    init(executable)

    parser = argparse.ArgumentParser(description=desc)
    add_input_args(parser, "List of files to encode", required=inputs_required)
    add_output_args(parser, "Output file or directory")

    parser.add_argument("--" + opt.Option.WIDTH, required=False, type=int, help="width of video/image")
    parser.add_argument("--" + opt.Option.HEIGHT, required=False, type=int, help="height of video/image")
    parser.add_argument(
        "-s",
        "--" + opt.Option.RESOLUTION,
        required=False,
        help="Media size WxH for videos and images, or an alias: 4k (3840x2160), 2.7k (2704x1520), 2.5k (2560x1440), "
        "fhd (1920x1080), hd (1280x720)...",
    )

    parser.add_argument("--aspect", required=False, help="Aspect Ratio eg 16:9, 4:3, 1.5 ...")

    add_verbosity_arg(parser)
    parser.add_argument("--keepName", required=False, default=False, action="store_true", help="Generate new file with same name as old")
    add_hw_accel_arg(parser)

    return parser


def add_hw_accel_arg(parser: argparse.ArgumentParser) -> None:
    """Adds the --hw_accel option to the parser of a tool"""
    parser.add_argument(
        "--hw_accel",
        required=False,
        choices=HW_ACCEL_MODES,
        help="Nvidia hardware acceleration: auto (default) uses it when available and falls back to the CPU if a command fails with it, "
        "on forces it, off disables it. Only used by the tools that decode or encode videos",
    )


def expand_input_files(inputs: list[str], input_type: str | tuple[str, ...] | None = None, extensions: tuple[str, ...] | None = None) -> list[str]:
    """Replaces the directories of a list of input files and directories by the files they contain (recursively).
    Exits with code 1 if there is no input file left"""
    files = fil.expand_inputs(inputs, input_type, extensions)
    if not files:
        log.logger.error("No input file found in %s", ", ".join(inputs))
        sys.exit(1)
    return files


FFMPEG_STATS_PERIOD = 2  # Interval in seconds between 2 progress lines of ffmpeg (0.5 by default)


class GlobalProgress:
    """Logs the global progress and ETA of a tool processing a collection of files, based on the number of files processed.
    The remaining files are assumed to be processed at the same speed as the ones already processed.
    While files are being processed, the progress of the file being processed (reported by the ffmpeg commands) is included
    in the global progress: 60% of the 7th file out of 11 is a global progress of (6 * 100 + 60) / 11 = 60%.
    Nothing is logged when there is a single file. Call done() each time a file has been processed.
    The steps may have different weights (by default 1 each, the total being the sum of the weights of all steps): the weight of
    the step being processed is set with next_weight before running it and passed to done()"""

    current: "GlobalProgress | None" = None  # The progress being tracked, used by the ffmpeg commands to display it

    def __init__(self, total: float) -> None:
        """Creates the progress of a tool processing steps whose weights sum up to total (1 for each file by default)"""
        self.total = total
        self.count: float = 0
        self.next_weight: float = 1
        self.start = time.time()
        GlobalProgress.current = self if total > 1 else None

    def eta(self, file_fraction: float = 0.0) -> tuple[float, str]:
        """Returns the global progress (0 to 1) and ETA when the file being processed is file_fraction (0 to 1) done"""
        fraction = min((self.count + file_fraction * self.next_weight) / self.total, 1.0)
        elapsed = time.time() - self.start
        return (fraction, to_hms_str(elapsed * (1 - fraction) / fraction if fraction > 0 else 0.0))

    def status(self, file_fraction: float) -> str:
        """Returns the global progress and ETA while the file being processed is file_fraction (0 to 1) done"""
        fraction, eta = self.eta(file_fraction)
        return f"Global progress {fraction * 100:.0f}%/ETA {eta}"

    def done(self, weight: float = 1) -> None:
        """Records that a step of a given weight is done, and logs the global progress and the ETA"""
        self.count += weight
        self.next_weight = 1
        if self.total <= 1:
            return
        fraction, eta = self.eta()
        log.logger.info("GLOBAL progress %g/%g - %d%%, ETA %s", self.count, self.total, fraction * 100, eta)
        if self.count >= self.total and GlobalProgress.current is self:
            GlobalProgress.current = None


def process_input_files(kwargs: dict, process: Callable[[str, dict], None]) -> None:
    """Calls process(input_file, options) on each of the input files, options being a copy of kwargs without the input files.
    An error on a file doesn't prevent the next files from being processed, but the program exits with code 1 at the end.
    Exits with code 2 if an output file is given with several input files"""
    options = dict(kwargs)
    inputs = options.pop(INPUT_FILES)
    if len(inputs) > 1 and options.get(OUTPUT_FILE):
        log.logger.error("-o can't be used with several input files")
        sys.exit(2)
    failed = 0
    progress = GlobalProgress(len(inputs))
    for i, input_file in enumerate(inputs, start=1):
        if len(inputs) > 1:
            log.logger.info("%3d/%3d : %s", i, len(inputs), input_file)
        try:
            process(input_file, dict(options))
        except Exception as e:
            log.logger.error("Could not process %s: %s", input_file, e)
            failed += 1
        progress.done()
    if failed:
        sys.exit(1)


def remove_nones(d: dict) -> dict:
    """Returns a dictionary without the items whose value is None"""
    return {k: v for k, v in d.items() if v is not None}


def parse_media_args(parser: argparse.ArgumentParser, args: list[str] | None = None, input_type: str | tuple[str, ...] | None = None) -> dict:
    """Parses the command line arguments.
    The input files (-i) may be files and/or directories: the directories are replaced by the files they contain (recursively),
    which are of type input_type (a FileType or a tuple of FileTypes), any audio/video/image file by default"""
    if args is None:
        kwargs = vars(parser.parse_args())
    else:
        kwargs = vars(parser.parse_args(args))
    # Default debug level is 3 = INFO (0 = CRITICAL, 1 = ERROR, 2 = WARNING, 3 = INFO, 4 = DEBUG)
    set_debug_level(get_verbosity(kwargs))
    log.logger.debug("Raw args = %s", str(kwargs))
    kwargs = {k: v for k, v in kwargs.items() if not isinstance(v, str) or v.strip() != ""}
    kwargs.pop("debug", None)
    kwargs.pop("verbosity", None)
    if kwargs.get(opt.Option.RESOLUTION):
        # The aliases (4k, 2.7k, fhd, hd, 2160p, 1520p, 1080p, 720p...) are converted to WxH: ffmpeg has its own, different, meaning for some of them
        kwargs[opt.Option.RESOLUTION] = res.canonical(kwargs[opt.Option.RESOLUTION])
    if isinstance(kwargs.get(INPUT_FILES), list):
        kwargs[INPUT_FILES] = expand_input_files(kwargs[INPUT_FILES], input_type)
    timerange = kwargs.get("timeranges")
    if timerange:
        timerange = timerange.split(",")[0]
    if timerange and "-" in timerange:
        kwargs[opt.Option.START], kwargs[opt.Option.STOP] = timerange.split("-")
    kwargs["hw_accel"] = get_hw_accel_mode(**kwargs)
    kwargs = remove_nones(kwargs)
    log.logger.debug("Processed args = %s", str(kwargs))
    return kwargs


def cleanup_options(kwargs: dict) -> dict:
    """Returns the options of a tool without the ones that are not for the media functions: None values, input and output files, profile"""
    new_options = remove_nones(kwargs)
    for key in [INPUT_FILES, OUTPUT_FILE, "profile"]:
        new_options.pop(key, None)
    return new_options


def get_profile_extension(profile: str | None, properties: dict | None = None) -> str | None:
    """Returns the extension of the output files of an encoding profile (mp4 by default)"""
    if profile is None:
        return "mp4"
    if properties is None:
        properties = get_media_properties()
    extension = properties.get(profile + ".extension", None)
    if extension is None:
        extension = properties.get("default.video.extension", None)
    return extension


def get_profile_params(profile: str | None) -> dict:
    """Returns the parameters of an encoding profile as a dictionary, an empty dictionary if there is no profile"""
    if profile is None:
        return {}
    props = get_media_properties()
    return get_cmdline_params(props[profile + ".cmdline"])


def get_cmdline_params(cmdline: str) -> dict:
    """Returns a dictionary of all parameters found on input string command line
    Parameters can be of the format -<option> <value> or -<option>"""
    found = True
    parms: dict = {}
    while found:
        # Remove heading spaces
        cmdline = re.sub(r"^\s+", "", cmdline)
        # Format -<option> <value>
        m = re.search(r"^-(\S+)\s+([A-Za-z0-9]\S*)", cmdline)
        if m:
            k = m.group(1)
            if k in opt.F2M_MAPPING:
                k = opt.M2F_MAPPING[opt.F2M_MAPPING[k]]
            parms[k] = m.group(2)
            cmdline = re.sub(r"^-(\S+)\s+([A-Za-z0-9]\S*)", "", cmdline)
        else:
            # Format -<option>
            m = re.search(r"^-(\S+)\s*", cmdline)
            if m:
                k = m.group(1)
                if k in opt.F2M_MAPPING:
                    k = opt.M2F_MAPPING[opt.F2M_MAPPING[k]]
                parms[k] = True
                cmdline = re.sub(r"^-(\S+)\s*", "", cmdline)
            else:
                found = False
    log.logger.debug("ffmpeg cmd line settings = %s", str(parms))
    return parms


def get_ffmpeg_cmdline_param(cmdline: str, param: str) -> str | None:
    """Returns the value of a parameter of an ffmpeg command line (-<param> <value>), None if it is not there"""
    m = re.search(rf"-{param}\s+(\S+)", cmdline)
    if m:
        return m.group(1)
    return None


def get_ffmpeg_cmdline_switch(cmdline: str, param: str) -> bool:
    """Returns True if an ffmpeg command line has a switch (-<param> without value)"""
    m = re.search(rf"-{param}\s", cmdline)
    return bool(m)


def get_ffmpeg_cmdline_params(cmdline: str) -> dict:
    """Returns the encoding parameters of an ffmpeg command line (codecs, bitrates, resolution, fps...) as a dictionary"""
    for o in [opt.OptionFfmpeg.ACODEC, opt.OptionFfmpeg.ACODEC2, opt.OptionFfmpeg.ACODEC3]:
        acodec = get_ffmpeg_cmdline_param(cmdline, o)
        if acodec is not None:
            break
    for o in [opt.OptionFfmpeg.VCODEC, opt.OptionFfmpeg.VCODEC2, opt.OptionFfmpeg.VCODEC3]:
        vcodec = get_ffmpeg_cmdline_param(cmdline, o)
        if vcodec is not None:
            break
    return remove_nones(
        {
            opt.Option.FORMAT: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.FORMAT),
            opt.Option.ABITRATE: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.ABITRATE),
            opt.Option.VBITRATE: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.VBITRATE),
            opt.Option.ACODEC: acodec,
            opt.Option.VCODEC: vcodec,
            opt.Option.RESOLUTION: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.RESOLUTION),
            opt.Option.FPS: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.FPS),
            opt.Option.ASPECT: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.ASPECT),
            opt.Option.VFILTER: get_ffmpeg_cmdline_param(cmdline, "vf"),
            opt.Option.ACHANNEL: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.ACHANNEL),
            opt.Option.DEINTERLACE: get_ffmpeg_cmdline_switch(cmdline, opt.OptionFfmpeg.DEINTERLACE),
            opt.Option.MUTE: get_ffmpeg_cmdline_switch(cmdline, opt.OptionFfmpeg.MUTE),
            opt.Option.VMUTE: get_ffmpeg_cmdline_switch(cmdline, opt.OptionFfmpeg.VMUTE),
            opt.Option.SAMPLERATE: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.SAMPLERATE),
        }
    )


def get_default_options(filetype: str = fil.FileType.VIDEO_FILE) -> dict:
    """Returns the default encoding options of the configuration file for audio or video files"""
    audio_opts = {
        opt.Option.ACODEC: get_conf_property("default.audio.codec"),
        opt.Option.ABITRATE: get_conf_property("default.audio.bitrate"),
        opt.Option.ACHANNEL: get_conf_property("default.audio.channels"),
        opt.Option.SAMPLERATE: get_conf_property("default.audio.samplerate"),
    }
    video_opts: dict = {}
    if filetype == fil.FileType.VIDEO_FILE:
        video_opts = {
            opt.Option.FORMAT: get_conf_property("default.video.format"),
            opt.Option.VCODEC: get_conf_property("default.video.codec"),
            opt.Option.VBITRATE: get_conf_property("default.video.bitrate"),
            opt.Option.FPS: get_conf_property("default.video.fps"),
            opt.Option.ASPECT: get_conf_property("default.video.aspect"),
            opt.Option.RESOLUTION: get_conf_property("default.video.resolution"),
        }
    return remove_nones({**audio_opts, **video_opts})


def get_profile_options(profile: str) -> dict:
    """Returns the encoding options of a profile of the configuration file"""
    return get_ffmpeg_cmdline_params(get_conf_property(profile + ".cmdline"))


def get_all_options(_filetype: str = fil.FileType.VIDEO_FILE, **cmdline_args: object) -> dict:
    """Returns the encoding options with the width and the height resolved. They are returned unchanged when audio and video are copied, and the
    bitrate of a copied stream is removed"""
    log.logger.debug("get_all_options(%s)", str(cmdline_args))
    if cmdline_args.get("vcodec") == "copy" and cmdline_args.get("acodec") == "copy":
        return cmdline_args
    if cmdline_args.get("acodec") == "copy":
        cmdline_args.pop("abitrate", None)
    if cmdline_args.get("vcodec") == "copy":
        cmdline_args.pop("vbitrate", None)
    cmdline_args[opt.Option.WIDTH], cmdline_args[opt.Option.HEIGHT] = resolve_resolution(**cmdline_args)
    log.logger.debug("get_all_options return: %s", str(cmdline_args))
    return cmdline_args


def swap_keys_values(p: dict) -> dict:
    """Returns a dictionary whose keys are the values of another one, and whose values are its keys"""
    return {v: k for k, v in p.items()}


def dict2str(options: dict) -> str:
    """Returns the options of a dictionary as the options of a command line (-key value, or -key for the switches)"""
    cmd = ""
    for k, v in options.items():
        if v is None or v is False:
            continue
        if v is True:
            fmt = f" -{k}"
        else:
            fmt = f" -{k} {v}"
        cmd += fmt
    log.logger.debug("cmd options = %s", cmd)
    return cmd


def find_key(hashlist: dict, keylist: list | tuple) -> object | None:
    """Returns the value of the first of the keys that is in a dictionary, None if there is none"""
    for key in keylist:
        if key not in hashlist:
            continue
        return hashlist[key]

    log.logger.warning("No key %s found in %s", str(keylist), str(hashlist))
    return None


def percent_or_absolute(x: str | float, reference: float = 1) -> float | int:
    """Converts a number or a percentage (eg 50%) to a number. A percentage is relative to a reference value"""
    if isinstance(x, str):
        if re.match(r"-?\d+(\.\d+)?%", x):
            return float(x[:-1]) * reference / 100
        return float(x)
    return x


def generated_file(filename: str) -> None:
    """Logs and displays the name of a file that was generated"""
    log.logger.info("Generated %s", filename)
    print(f"Generated {filename}")


def package_home() -> pathlib.Path:
    """Returns the directory of the package"""
    return pathlib.Path(__file__).parent


def get_tmp_file() -> str:
    """Returns the name of a temporary file (the file is not created)"""
    return tempfile.gettempdir() + os.sep + uuid.uuid4().hex[:8]


def resolve_resolution(**kwargs: object) -> tuple[int | None, int | None]:
    """Returns the width and the height requested by the width, height and resolution options. A missing dimension is -1, (None, None) means no
    dimension"""
    log.logger.info("ARgs = %s", str(kwargs))
    if kwargs.get(opt.Option.WIDTH):
        if kwargs.get(opt.Option.HEIGHT):
            return (kwargs[opt.Option.WIDTH], kwargs[opt.Option.HEIGHT])
        return (kwargs[opt.Option.WIDTH], -1)
    if kwargs.get(opt.Option.HEIGHT):
        return (-1, kwargs[opt.Option.HEIGHT])
    if kwargs.get(opt.Option.RESOLUTION) is None:
        return (None, None)

    kwargs[opt.Option.RESOLUTION] = res.canonical(kwargs[opt.Option.RESOLUTION])
    w, h = kwargs[opt.Option.RESOLUTION].split("x", maxsplit=2)
    w = int(w) if w != "" else -1
    h = int(h) if h != "" else -1
    return (w, h)


def get_hw_accel_mode(**kwargs: object) -> str:
    """Returns the hardware acceleration mode: auto, on or off.
    It's the value of the hw_accel option (a boolean means on / off), or the default.hw_accel property, or auto"""
    value = kwargs.get("hw_accel")
    if value is None:
        value = conf.get_property("default.hw_accel")
    if isinstance(value, bool):
        return "on" if value else "off"
    value = str(value).strip().lower() if value is not None else "auto"
    return value if value in HW_ACCEL_MODES else "auto"


def check_hardware_accel() -> bool:
    """Checks (once) whether the hardware acceleration can be used, by encoding a few frames with it"""
    global HW_ACCEL
    if HW_ACCEL is not None:
        return HW_ACCEL
    log.logger.info("Checking if hardware acceleration can be used")
    outputfile = get_tmp_file() + ".mp4"
    inputfile = str(package_home() / "video-720p.mp4")
    try:
        log.logger.debug("Trying to encode 1 second of %s", inputfile)
        run_ffmpeg(f'{HW_ACCEL_PREFIX} -ss 0 -i "{inputfile}" -vf scale_cuda=640:-1 -c:a copy -c:v h264_nvenc -to 2 "{outputfile}"')
        os.remove(outputfile)
        HW_ACCEL = True
    except subprocess.CalledProcessError:
        HW_ACCEL = False
    log.logger.info("Auto hardware acceleration = %s", str(HW_ACCEL))
    return HW_ACCEL


def use_hardware_accel(**kwargs: object) -> bool:
    """Returns whether the hardware acceleration must be used (hw_accel option: auto, on or off).
    In auto mode it's used if it's available, unless the command is being retried on the CPU, see hw_accel_fallback()"""
    if _hw_forced_off.get():
        return False
    mode = get_hw_accel_mode(**kwargs)
    log.logger.debug("hw accel = %s", mode)
    if mode == "on":
        log.logger.info("Hardware acceleration explicitly forced on")
        return True
    if mode == "off":
        log.logger.info("Hardware acceleration explicitly turned off")
        return False
    if kwargs.get(opt.Option.DEINTERLACE, False):
        # Deinterlacing is incompatible with HW accel
        log.logger.info("Not using hardware acceleration because of deinterlace")
        return False
    return check_hardware_accel()


def _call_options(func: Callable, args: tuple, kwargs: dict) -> dict:
    """Returns the options of a call that are relevant to know whether hardware acceleration is used"""
    options = dict(kwargs)
    try:
        signature = inspect.signature(func)
        bound = signature.bind_partial(*args, **kwargs).arguments
    except (TypeError, ValueError):
        return options
    for name, param in signature.parameters.items():
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            options.update(bound.get(name, {}))
        elif name in ("hw_accel", opt.Option.DEINTERLACE) and name in bound:
            options[name] = bound[name]
    return options


def hw_accel_fallback(func: Callable) -> Callable:
    """Decorator of the functions that decode or encode videos with ffmpeg and use the hardware acceleration if use_hardware_accel().
    In auto mode, if a hardware accelerated ffmpeg command fails, the whole function is run again on the CPU.
    With the on mode the failure is raised, with the off mode the hardware acceleration is not used.
    The function must get its hardware acceleration option as hw_accel (argument or keyword argument)"""

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> object:
        """Runs the function, and runs it again on the CPU if the hardware acceleration was used and the function failed in auto mode"""
        options = _call_options(func, args, kwargs)
        if _hw_attempt_depth.get() > 0 or _hw_forced_off.get() or get_hw_accel_mode(**options) != "auto" or not use_hardware_accel(**options):
            # Nothing to retry: the CPU is used, the hardware acceleration is forced, or an outer function already handles the fallback
            return func(*args, **kwargs)
        commands: list = []
        depth_token = _hw_attempt_depth.set(_hw_attempt_depth.get() + 1)
        commands_token = _hw_command_run.set(commands)
        try:
            return func(*args, **kwargs)
        except subprocess.CalledProcessError as e:
            if not commands:
                raise  # No hardware accelerated command was run, running again on the CPU would fail the same way
            log.logger.warning(
                "A command failed with hardware acceleration (%s), trying again with the CPU", e.output or f"return code {e.returncode}"
            )
        finally:
            _hw_command_run.reset(commands_token)
            _hw_attempt_depth.reset(depth_token)
        forced_token = _hw_forced_off.set(True)
        try:
            return func(*args, **kwargs)
        finally:
            _hw_forced_off.reset(forced_token)

    return wrapper


def get_creation_date(exif_data: dict) -> datetime | None:
    """Returns the creation date found in the EXIF data of a file, None if there is none"""
    str_date: str | None = None
    creation_date: datetime | None = None
    for tag in CREATION_DATE_TAGS:
        tag_val = exif_data.get(tag, "")
        if tag_val != "" and int(tag_val[0:4]) > 1970:
            str_date = tag_val
            break
    if str_date is None:
        log.logger.warning("Can't find creation date in %s", json_fmt(exif_data))
        return None

    if str_date == "0000:00:00 00:00:00":
        str_date = "1900:01:01 00:00:00"
    for fmt in DATE_FORMATS:
        try:
            creation_date = datetime.strptime(str_date, fmt)
            break
        except ValueError:
            pass
    if creation_date is None:
        raise ValueError
    return creation_date
