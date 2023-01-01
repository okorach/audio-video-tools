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
import platform
import json
import logging
import re
import argparse
import pathlib
import tempfile
import subprocess
import shlex
from mediatools import version
from mediatools import log
import mediatools.options as opt
import mediatools.resolution as res
import mediatools.file as fil
import mediatools.media_config as conf

DEBUG_LEVEL = 0
DRY_RUN = False
HW_ACCEL = None
HW_ACCEL_PREFIX = "-hwaccel cuda -hwaccel_output_format cuda"

LANGUAGE_MAPPING = {'fre': 'French', 'eng': 'English'}

OPTIONS_VERBATIM = ['ss', 'to']

config_props = os.path.realpath(__file__).split(os.path.sep)
config_props.pop()
config_props.pop()
config_props.append("media-tools.properties")
DEFAULT_PROPERTIES_FILE = os.path.sep.join(config_props)
# log.logger.debug("Default properties file = %s", DEFAULT_PROPERTIES_FILE)

PROPERTIES_FILE = ''
PROPERTIES_VALUES = {}


def add_postfix(file, postfix, extension=None):
    """Adds a postfix to a file before the file extension"""
    if extension is None:
        extension = conf.get_property(f'default.{fil.get_type(file)}.format')
    if extension is None:
        extension = fil.extension(file)
    return fil.strip_extension(file) + r'.' + postfix + r'.' + extension


def automatic_output_file_name(outfile, infile, postfix, extension=None):
    if outfile is not None:
        return outfile
    postfix.replace(':', '-')
    return add_postfix(infile, postfix, extension)


def get_ffbin(ffprop):
    props = get_media_properties()

    if not re.search('\\' + os.path.sep, props[ffprop]):
        return props[ffprop]
    return props[ffprop]      # os.path.realpath(props[ffprop])


def get_ffmpeg():
    return get_ffbin('binaries.ffmpeg')


def get_ffprobe():
    return get_ffbin('binaries.ffprobe')


def get_first_value(a_dict, key_list):
    if a_dict is None:
        return None
    for tag in key_list:
        if tag in a_dict:
            return a_dict[tag]
    return None


def __compute_eta__(line, total_time):
    if total_time is None:
        return ''
    # m = re.search(r"frame=\s*\d+ fps=[\d\.]+ q=[\d\.]+ size=\s*\d+kB time=(\d+:\d+:\d+\.\d+) "
    #               r"bitrate=\s*[\d\.]+kbits\/s dup=\d+ drop=\d+ speed=\s*([\d\.]+)x", line)
    m = re.search(r"size=.* time=(\d+:\d+:\d+\.\d+)\s+bitrate=.*speed=\s*([\d\.]+)x", line)
    if not m:
        log.logger.debug("%s does not match %s", line, r"size=.* time=(\d+:\d+:\d+\.\d+)\s+bitrate=.*speed=\s*([\d\.]+)x")
        return ''
    speed = float(m.group(2))
    if speed == 0:
        return " ETA=Undefined"
    return " ETA=" + to_hms_str(max(0, (total_time - to_seconds(m.group(1))) / speed))


def __get_log_level_from_ffmpeg_log__(line):
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

def run_os_cmd(cmd, total_time=None):
    log.logger.info("Running: %s", cmd)
    if total_time is not None and isinstance(total_time, str):
        total_time = to_seconds(total_time)
    try:
        last_error_line, same_error_count = None, 0
        current_log_level, last_log_level = logging.INFO, logging.INFO
        args = shlex.split(cmd)
        pipe = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, bufsize=1)
        line = pipe.stdout.readline().rstrip()
        while line:
            current_log_level = __get_log_level_from_ffmpeg_log__(line)
            line += __compute_eta__(line, total_time)
            if last_error_line is not None and last_error_line == line:
                same_error_count += 1
            else:
                if same_error_count > 1:
                    log.logger.log(last_log_level, "Above error repeated %d times...", same_error_count)
                log.logger.log(current_log_level, line)
                same_error_count = 1
                last_error_line = line

            line = pipe.stdout.readline().rstrip()
        outs, errs = pipe.communicate()
        log.logger.debug("Return code = %d", pipe.returncode)
        if pipe.returncode not in (0, 3221225477):     # TODO: Better than this ugly hack for ffmpeg
            last_error_line = line if last_error_line is None else last_error_line
            raise subprocess.CalledProcessError(cmd=cmd, output=last_error_line, returncode=pipe.returncode)
        log.logger.info("Successfully completed: %s", cmd)
    except subprocess.CalledProcessError as e:
        log.logger.error("Command: %s failed with return code %d", cmd, e.returncode)
        log.logger.error("%s", e.output)
        raise e


def run_ffmpeg(params, duration=None):
    quot = '"' if platform.system() == 'Windows' else ""
    cmd = f'{quot}{get_ffmpeg()}{quot} -y {params}'
    run_os_cmd(cmd, duration)


def build_ffmpeg_complex_prep(input_file_list):
    s = ''
    for i in range(len(input_file_list) + 1):
        s += "[{0}]scale=iw:-1:flags=lanczos[pip{0}]; ".format(i)
    return s


def get_media_properties():
    """Returns all properties found in the properties file as dictionary"""
    global PROPERTIES_VALUES
    if not PROPERTIES_VALUES:
        PROPERTIES_VALUES = conf.load()
        log.logger.debug("Props = %s", str(PROPERTIES_VALUES))
    return PROPERTIES_VALUES


def get_conf_property(prop):
    global PROPERTIES_VALUES
    if not PROPERTIES_VALUES:
        get_media_properties()
    return PROPERTIES_VALUES[prop]


def to_hms(seconds, fmt='tuple'):
    try:
        s = int(float(seconds))
        hours = s // 3600
        minutes = s // 60 - hours * 60
        secs = round(float(seconds) - hours * 3600 - minutes * 60, 3)
        if fmt == 'string':
            return "%02d:%02d:%06.3f" % (hours, minutes, secs)
        else:
            return (hours, minutes, secs)
    except (TypeError, ValueError):
        if fmt == 'string':
            return "00:00:00"
        else:
            return (0, 0, 0)


def to_seconds(hms):
    a = [float(x) for x in str(hms).split(':')]
    if len(a) == 3:
        return a[0] * 3600 + a[1] * 60 + a[2]
    elif len(a) == 2:
        return a[0] * 60 + a[1]
    else:
        return a[0]


def difftime(stop, start):
    return to_seconds(stop) - to_seconds(start)


def to_hms_str(seconds):
    hours, minutes, secs = to_hms(seconds)
    return "%02d:%02d:%06.3f" % (hours, minutes, secs)


def json_fmt(json_data):
    return json.dumps(json_data, sort_keys=True, indent=3, separators=(',', ': '))


def set_debug_level(level):
    global DEBUG_LEVEL
    DEBUG_LEVEL = 3 if level is None else int(level)
    log.logger.setLevel(log.get_logging_level(DEBUG_LEVEL))
    log.logger.info("Set debug level to %d", DEBUG_LEVEL)


def init(logger_name):
    log.set_logger(logger_name)
    log.logger.setLevel(log.get_logging_level(3))
    log.logger.info('audio-video-tools version %s', version.MEDIA_TOOLS_VERSION)


def delete_files(*args):
    for f in args:
        log.logger.debug("Deleting file %s", f)
        os.remove(f)


def get_common_args(executable, desc):
    """Parses options common to all media encoding scripts"""

    init(executable)

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-i', '--inputfile', required=True, help='Input file or directory to encode')
    parser.add_argument('-o', '--outputfile', required=False, help='Output file or directory')

    parser.add_argument('--' + opt.Option.WIDTH, required=False, type=int, help='width of video/image')
    parser.add_argument('--' + opt.Option.HEIGHT, required=False, type=int, help='height of video/image')
    parser.add_argument('-s', '--' + opt.Option.RESOLUTION, required=False, help='Media size HxW for videos and images')

    parser.add_argument('--aspect', required=False, help='Aspect Ratio eg 16:9, 4:3, 1.5 ...')

    parser.add_argument('-g', '--debug', required=False, help='Debug level')

    return parser


def remove_nones(p):
    return dict((k, v) for k, v in p.items() if v is not None)


def parse_media_args(parser, args=None):
    if args is None:
        kwargs = vars(parser.parse_args())
    else:
        kwargs = vars(parser.parse_args(args))
    # Default debug level is 3 = INFO (0 = CRITICAL, 1 = ERROR, 2 = WARNING, 3 = INFO, 4 = DEBUG)
    set_debug_level(kwargs.get('debug', 3))
    log.logger.debug('Raw args = %s', str(kwargs))
    kwargs.pop('debug')
    (kwargs[opt.Option.WIDTH], kwargs[opt.Option.HEIGHT]) = resolve_resolution(**kwargs)
    timerange = kwargs.get('timeranges', None)
    if timerange:
        timerange = timerange.split(',')[0]
    if timerange and '-' in timerange:
        kwargs[opt.Option.START], kwargs[opt.Option.STOP] = timerange.split('-')
    if kwargs.get('hw_accel', None) is None:
        kwargs['hw_accel'] = conf.get_property('default.hw_accel')
    if kwargs.get('hw_accel', None) is None:
        kwargs['hw_accel'] = 'auto'

    if kwargs.get('hw_accel', None) == 'on':
        kwargs['hw_accel'] = True
    elif kwargs.get('hw_accel', None) == 'off':
        kwargs['hw_accel'] = False
    else:
        kwargs['hw_accel'] = use_hardware_accel(**kwargs)
    kwargs = remove_nones(kwargs)
    log.logger.debug('Processed args = %s', str(kwargs))
    return kwargs


def cleanup_options(kwargs):
    new_options = remove_nones(kwargs)
    for key in ['inputfile', 'outputfile', 'profile']:
        new_options.pop(key, None)
    return new_options


def get_profile_extension(profile, properties=None):
    if profile is None:
        return 'mp4'
    if properties is None:
        properties = get_media_properties()
    extension = properties.get(profile + '.extension', None)
    if extension is None:
        extension = properties.get('default.video.extension', None)
    return extension


def get_profile_params(profile):
    if profile is None:
        return {}
    props = get_media_properties()
    return get_cmdline_params(props[profile + '.cmdline'])


def get_cmdline_params(cmdline):
    """Returns a dictionary of all parameters found on input string command line
    Parameters can be of the format -<option> <value> or -<option>"""
    found = True
    parms = {}
    while found:
        # Remove heading spaces
        cmdline = re.sub(r'^\s+', '', cmdline)
        # Format -<option> <value>
        m = re.search(r'^-(\S+)\s+([A-Za-z0-9]\S*)', cmdline)
        if m:
            k = m.group(1)
            if k in opt.F2M_MAPPING:
                k = opt.M2F_MAPPING[opt.F2M_MAPPING[k]]
            parms[k] = m.group(2)
            cmdline = re.sub(r'^-(\S+)\s+([A-Za-z0-9]\S*)', '', cmdline)
        else:
            # Format -<option>
            m = re.search(r'^-(\S+)\s*', cmdline)
            if m:
                k = m.group(1)
                if k in opt.F2M_MAPPING:
                    k = opt.M2F_MAPPING[opt.F2M_MAPPING[k]]
                parms[k] = True
                cmdline = re.sub(r'^-(\S+)\s*', '', cmdline)
            else:
                found = False
    log.logger.debug("ffmpeg cmd line settings = %s", str(parms))
    return parms


def get_ffmpeg_cmdline_param(cmdline, param):
    m = re.search(rf"-{param}\s+(\S+)", cmdline)
    if m:
        return m.group(1)
    return None


def get_ffmpeg_cmdline_switch(cmdline, param):
    m = re.search(rf'-{param}\s', cmdline)
    if m:
        return True
    return False


def get_ffmpeg_cmdline_params(cmdline):
    for o in [opt.OptionFfmpeg.ACODEC, opt.OptionFfmpeg.ACODEC2, opt.OptionFfmpeg.ACODEC3]:
        acodec = get_ffmpeg_cmdline_param(cmdline, o)
        if acodec is not None:
            break
    for o in [opt.OptionFfmpeg.VCODEC, opt.OptionFfmpeg.VCODEC2, opt.OptionFfmpeg.VCODEC3]:
        vcodec = get_ffmpeg_cmdline_param(cmdline, o)
        if vcodec is not None:
            break
    return remove_nones({
        opt.Option.FORMAT: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.FORMAT),
        opt.Option.ABITRATE: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.ABITRATE),
        opt.Option.VBITRATE: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.VBITRATE),
        opt.Option.ACODEC: acodec,
        opt.Option.VCODEC: vcodec,
        opt.Option.RESOLUTION: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.RESOLUTION),
        opt.Option.FPS: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.FPS),
        opt.Option.ASPECT: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.ASPECT),
        opt.Option.VFILTER: get_ffmpeg_cmdline_param(cmdline, 'vf'),
        opt.Option.ACHANNEL: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.ACHANNEL),
        opt.Option.DEINTERLACE: get_ffmpeg_cmdline_switch(cmdline, opt.OptionFfmpeg.DEINTERLACE),
        opt.Option.MUTE: get_ffmpeg_cmdline_switch(cmdline, opt.OptionFfmpeg.MUTE),
        opt.Option.VMUTE: get_ffmpeg_cmdline_switch(cmdline, opt.OptionFfmpeg.VMUTE),
        opt.Option.SAMPLERATE: get_ffmpeg_cmdline_param(cmdline, opt.OptionFfmpeg.SAMPLERATE)
    })

def get_default_options(filetype=fil.FileType.VIDEO_FILE):
    audio_opts = {
        opt.Option.ACODEC: get_conf_property('default.audio.codec'),
        opt.Option.ABITRATE: get_conf_property('default.audio.bitrate'),
        opt.Option.ACHANNEL: get_conf_property('default.audio.channels'),
        opt.Option.SAMPLERATE: get_conf_property('default.audio.samplerate')
    }
    video_opts = {}
    if filetype == fil.FileType.VIDEO_FILE:
        video_opts = {
            opt.Option.FORMAT: get_conf_property('default.video.format'),
            opt.Option.VCODEC: get_conf_property('default.video.codec'),
            opt.Option.VBITRATE: get_conf_property('default.video.bitrate'),
            opt.Option.FPS: get_conf_property('default.video.fps'),
            opt.Option.ASPECT: get_conf_property('default.video.aspect'),
            opt.Option.RESOLUTION: get_conf_property('default.video.resolution')
        }
    return remove_nones({**audio_opts, **video_opts})

def get_profile_options(profile):
    return get_ffmpeg_cmdline_params(get_conf_property(profile + '.cmdline'))

def get_all_options(filetype=fil.FileType.VIDEO_FILE, **cmdline_args):
    log.logger.debug("get_all_options(%s)", str(cmdline_args))
    if cmdline_args.get('vcodec', None) == 'copy' and cmdline_args.get('acodec', None) == 'copy':
        return cmdline_args
    p = get_default_options(filetype)
    if 'profile' in cmdline_args:
        q = get_profile_options(cmdline_args['profile'])
        p = {**p, **q}
    cmdline_args = {**p, **cmdline_args}
    if cmdline_args.get('acodec', None) == 'copy':
        cmdline_args.pop('abitrate', None)
    if cmdline_args.get('vcodec', None) == 'copy':
        cmdline_args.pop('vbitrate', None)
    (cmdline_args[opt.Option.WIDTH], cmdline_args[opt.Option.HEIGHT]) = resolve_resolution(**cmdline_args)
    log.logger.debug("get_all_options return: %s", str(cmdline_args))
    return cmdline_args


def swap_keys_values(p):
    return {v: k for k, v in p.items()}


def dict2str(options):
    cmd = ''
    for k in options:
        if options[k] is None or options[k] is False:
            continue
        if options[k] is True:
            fmt = f" -{k}"
        else:
            fmt = f" -{k} {options[k]}"
        cmd += fmt
    log.logger.debug("cmd options = %s", cmd)
    return cmd


def find_key(hashlist, keylist):
    for key in keylist:
        if key not in hashlist:
            continue
        return hashlist[key]

    log.logger.warning("No key %s found in %s", str(keylist), str(hashlist))
    return None


def percent_or_absolute(x, reference=1):
    if isinstance(x, str):
        if re.match(r'-?\d+(.\d+)?%', x):
            return float(x[:-1]) * reference / 100
        else:
            return float(x)
    return x


def generated_file(filename):
    log.logger.info("Generated %s", filename)
    print(f"Generated {filename}")


def package_home():
    return pathlib.Path(__file__).parent


def get_tmp_file():
    return tempfile.gettempdir() + os.sep + next(tempfile._get_candidate_names())


def resolve_resolution(**kwargs):
    log.logger.info("ARgs = %s", str(kwargs))
    if kwargs.get(opt.Option.WIDTH, None):
        if kwargs.get(opt.Option.HEIGHT, None):
            return (kwargs[opt.Option.WIDTH], kwargs[opt.Option.HEIGHT])
        else:
            return (kwargs[opt.Option.WIDTH], -1)
    else:
        if kwargs.get(opt.Option.HEIGHT, None):
            return (-1, kwargs[opt.Option.HEIGHT])
    if kwargs.get(opt.Option.RESOLUTION, None) is None:
        return (None, None)

    kwargs[opt.Option.RESOLUTION] = res.canonical(kwargs[opt.Option.RESOLUTION])
    w, h = kwargs[opt.Option.RESOLUTION].split('x', maxsplit=2)
    w = int(w) if w != '' else -1
    h = int(h) if h != '' else -1
    return (w, h)


def use_hardware_accel(**kwargs):
    global HW_ACCEL
    my_hw_accel = kwargs.get('hw_accel', 'auto')
    log.logger.debug("my hw accel = %s", str(my_hw_accel))
    if (isinstance(my_hw_accel, bool) and my_hw_accel) or my_hw_accel == 'on':
        HW_ACCEL = True
        log.logger.info("Hardware acceleration explicitly forced on")
        return True
    elif (isinstance(my_hw_accel, bool) and not my_hw_accel) or my_hw_accel == 'off':
        HW_ACCEL = False
        log.logger.info("Hardware acceleration explicitly turned off")
        return False

    if kwargs.get(opt.Option.DEINTERLACE, False):
        # Deinterlacing is incompatible with HW accel
        log.logger.info("Turning off hardware acceleration because of deinterlace")
        HW_ACCEL = False
    if my_hw_accel != 'auto':
        HW_ACCEL = False
    if HW_ACCEL is not None:
        return HW_ACCEL

    # Auto mode, test execution with HW acceleration
    log.logger.info("Checking if hardware acceleration can be used")
    outputfile = get_tmp_file() + '.mp4'
    inputfile = str(package_home() / 'video-720p.mp4')
    try:
        log.logger.debug("Trying to encode 1 second of %s", inputfile)
        run_ffmpeg(f'{HW_ACCEL_PREFIX} -ss 0 -i "{inputfile}" -vf scale_cuda=640:-1 -c:a copy -c:v h264_nvenc -to 2 "{outputfile}"')
        os.remove(outputfile)
        HW_ACCEL = True
    except subprocess.CalledProcessError:
        HW_ACCEL = False
    log.logger.info("Auto hardware acceleration = %s", str(HW_ACCEL))
    return HW_ACCEL
