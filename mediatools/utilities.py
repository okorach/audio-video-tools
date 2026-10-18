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

import os
import sys
import platform
import functools
import inspect
import contextvars
import json
import logging
import re
import argparse
import pathlib
import tempfile
import uuid
import subprocess
import shlex
from collections.abc import Callable
from datetime import datetime
from mediatools import version
from mediatools import log
import mediatools.options as opt
import mediatools.resolution as res
import utilities.file as fil
import mediatools.media_config as conf
from mediatools import metacopy

DEBUG_LEVEL: int = 0
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
# log.logger.debug("Default properties file = %s", DEFAULT_PROPERTIES_FILE)

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
    if outfile is not None:
        return outfile
    postfix.replace(":", "-")
    return add_postfix(infile, postfix, extension)


def get_ffbin(ffprop: str) -> str:
    props = get_media_properties()

    if not re.search("\\" + os.path.sep, props[ffprop]):
        return props[ffprop]
    return props[ffprop]  # os.path.realpath(props[ffprop])


def get_ffmpeg() -> str:
    return get_ffbin("binaries.ffmpeg")


def get_ffprobe() -> str:
    return get_ffbin("binaries.ffprobe")


def get_exiftool() -> str:
    return get_media_properties().get("binaries.exiftool", "exiftool")


def get_first_value(a_dict: dict | None, key_list: tuple | list):
    if a_dict is None:
        return None
    for tag in key_list:
        if tag in a_dict:
            return a_dict[tag]
    return None


def __compute_eta__(line: str, total_time: float | str | None) -> str:
    if total_time is None:
        return ""
    # m = re.search(r"frame=\s*\d+ fps=[\d\.]+ q=[\d\.]+ size=\s*\d+kB time=(\d+:\d+:\d+\.\d+) "
    #               r"bitrate=\s*[\d\.]+kbits\/s dup=\d+ drop=\d+ speed=\s*([\d\.]+)x", line)
    m = re.search(r"size=.* time=(\d+:\d+:\d+\.\d+)\s+bitrate=.*speed=\s*([\d\.]+)x", line)
    if not m:
        log.logger.debug("%s does not match %s", line, r"size=.* time=(\d+:\d+:\d+\.\d+)\s+bitrate=.*speed=\s*([\d\.]+)x")
        return ""
    speed = float(m.group(2))
    if speed == 0:
        return " ETA=Undefined"
    return " ETA=" + to_hms_str(max(0, (total_time - to_seconds(m.group(1))) / speed))


def __get_log_level_from_ffmpeg_log__(line: str) -> int:
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
    commands = _hw_command_run.get()
    if commands is not None and HW_ACCEL_COMMAND_REGEXP.search(params):
        commands.append(params)  # Remember that a hardware accelerated command was run, see hw_accel_fallback()
    quot = '"' if platform.system() == "Windows" else ""
    cmd = f"{quot}{get_ffmpeg()}{quot} -y {params}"
    run_os_cmd(cmd, duration)
    metacopy.copy_after_ffmpeg(params)


def build_ffmpeg_complex_prep(input_file_list: list) -> str:
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


def get_conf_property(prop: str):
    global PROPERTIES_VALUES
    if not PROPERTIES_VALUES:
        get_media_properties()
    return PROPERTIES_VALUES[prop]


def to_hms(seconds: float | str, fmt: str = "tuple") -> tuple[int, int, float] | str:
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
    a = [float(x) for x in str(hms).split(":")]
    if len(a) == 3:
        return a[0] * 3600 + a[1] * 60 + a[2]
    if len(a) == 2:
        return a[0] * 60 + a[1]
    return a[0]


def difftime(stop: float | str, start: float | str) -> float:
    return to_seconds(stop) - to_seconds(start)


def to_hms_str(seconds: float) -> str:
    hours, minutes, secs = to_hms(seconds)
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def json_fmt(json_data: object) -> str:
    return json.dumps(json_data, sort_keys=True, indent=3, separators=(",", ": "))


def set_debug_level(level: int | str | None) -> None:
    global DEBUG_LEVEL
    DEBUG_LEVEL = 3 if level is None else int(level)
    log.logger.setLevel(log.get_logging_level(DEBUG_LEVEL))
    log.logger.info("Set debug level to %d", DEBUG_LEVEL)


def init(logger_name: str) -> None:
    log.set_logger(logger_name)
    log.logger.setLevel(log.get_logging_level(3))
    log.logger.info("audio-video-tools version %s", version.MEDIA_TOOLS_VERSION)


def delete_files(*args: str) -> None:
    for f in args:
        log.logger.debug("Deleting file %s", f)
        os.remove(f)


def get_common_args(executable: str, desc: str) -> argparse.ArgumentParser:
    """Parses options common to all media encoding scripts"""
    init(executable)

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("-i", "--inputfiles", required=True, metavar="N", type=str, nargs="+", help="List of files to encode")
    parser.add_argument("-o", "--outputfile", required=False, help="Output file or directory")

    parser.add_argument("--" + opt.Option.WIDTH, required=False, type=int, help="width of video/image")
    parser.add_argument("--" + opt.Option.HEIGHT, required=False, type=int, help="height of video/image")
    parser.add_argument("-s", "--" + opt.Option.RESOLUTION, required=False, help="Media size HxW for videos and images")

    parser.add_argument("--aspect", required=False, help="Aspect Ratio eg 16:9, 4:3, 1.5 ...")

    parser.add_argument("-g", "--debug", required=False, help="Debug level")
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


def process_input_files(kwargs: dict, process: Callable[[str, dict], None]) -> None:
    """Calls process(input_file, options) on each of the input files, options being a copy of kwargs without the input files.
    An error on a file doesn't prevent the next files from being processed, but the program exits with code 1 at the end.
    Exits with code 2 if an output file is given with several input files"""
    options = dict(kwargs)
    inputs = options.pop("inputfiles")
    if len(inputs) > 1 and options.get("outputfile"):
        log.logger.error("-o can't be used with several input files")
        sys.exit(2)
    failed = 0
    for i, input_file in enumerate(inputs, start=1):
        if len(inputs) > 1:
            log.logger.info("%3d/%3d : %s", i, len(inputs), input_file)
        try:
            process(input_file, dict(options))
        except Exception as e:
            log.logger.error("Could not process %s: %s", input_file, e)
            failed += 1
    if failed:
        sys.exit(1)


def remove_nones(d: dict) -> dict:
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
    set_debug_level(kwargs.get("debug", 3))
    log.logger.debug("Raw args = %s", str(kwargs))
    kwargs = {k: v for k, v in kwargs.items() if not isinstance(v, str) or v.strip() != ""}
    kwargs.pop("debug", None)
    if isinstance(kwargs.get("inputfiles"), list):
        kwargs["inputfiles"] = expand_input_files(kwargs["inputfiles"], input_type)
    # (kwargs[opt.Option.WIDTH], kwargs[opt.Option.HEIGHT]) = resolve_resolution(**kwargs)
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
    new_options = remove_nones(kwargs)
    for key in ["inputfiles", "outputfile", "profile"]:
        new_options.pop(key, None)
    return new_options


def get_profile_extension(profile: str | None, properties: dict | None = None) -> str | None:
    if profile is None:
        return "mp4"
    if properties is None:
        properties = get_media_properties()
    extension = properties.get(profile + ".extension", None)
    if extension is None:
        extension = properties.get("default.video.extension", None)
    return extension


def get_profile_params(profile: str | None) -> dict:
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
    m = re.search(rf"-{param}\s+(\S+)", cmdline)
    if m:
        return m.group(1)
    return None


def get_ffmpeg_cmdline_switch(cmdline: str, param: str) -> bool:
    m = re.search(rf"-{param}\s", cmdline)
    return bool(m)


def get_ffmpeg_cmdline_params(cmdline: str) -> dict:
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
    return get_ffmpeg_cmdline_params(get_conf_property(profile + ".cmdline"))


def get_all_options(filetype: str = fil.FileType.VIDEO_FILE, **cmdline_args) -> dict:
    log.logger.debug("get_all_options(%s)", str(cmdline_args))
    if cmdline_args.get("vcodec") == "copy" and cmdline_args.get("acodec") == "copy":
        return cmdline_args
    # p = get_default_options(filetype)
    # if 'profile' in cmdline_args:
    #    q = get_profile_options(cmdline_args['profile'])
    #    p = {**p, **q}
    # cmdline_args = {**p, **cmdline_args}
    if cmdline_args.get("acodec") == "copy":
        cmdline_args.pop("abitrate", None)
    if cmdline_args.get("vcodec") == "copy":
        cmdline_args.pop("vbitrate", None)
    cmdline_args[opt.Option.WIDTH], cmdline_args[opt.Option.HEIGHT] = resolve_resolution(**cmdline_args)
    log.logger.debug("get_all_options return: %s", str(cmdline_args))
    return cmdline_args


def swap_keys_values(p: dict) -> dict:
    return {v: k for k, v in p.items()}


def dict2str(options: dict) -> str:
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


def find_key(hashlist: dict, keylist: list | tuple):
    for key in keylist:
        if key not in hashlist:
            continue
        return hashlist[key]

    log.logger.warning("No key %s found in %s", str(keylist), str(hashlist))
    return None


def percent_or_absolute(x: str | float, reference: float = 1) -> float | int:
    if isinstance(x, str):
        if re.match(r"-?\d+(.\d+)?%", x):
            return float(x[:-1]) * reference / 100
        return float(x)
    return x


def generated_file(filename: str) -> None:
    log.logger.info("Generated %s", filename)
    print(f"Generated {filename}")


def package_home() -> pathlib.Path:
    return pathlib.Path(__file__).parent


def get_tmp_file() -> str:
    return tempfile.gettempdir() + os.sep + uuid.uuid4().hex[:8]


def resolve_resolution(**kwargs) -> tuple[int | None, int | None]:
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


def get_hw_accel_mode(**kwargs) -> str:
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


def use_hardware_accel(**kwargs) -> bool:
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
