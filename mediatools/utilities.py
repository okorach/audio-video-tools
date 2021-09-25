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

LANGUAGE_MAPPING = {'fre': 'French', 'eng': 'English'}

OPTIONS_VERBATIM = ['ss', 'to']

config_props = os.path.realpath(__file__).split(os.path.sep)
config_props.pop()
config_props.pop()
config_props.append("media-tools.properties")
DEFAULT_PROPERTIES_FILE = os.path.sep.join(config_props)
log.logger.debug("Default properties file = %s", DEFAULT_PROPERTIES_FILE)

PROPERTIES_FILE = ''
PROPERTIES_VALUES = {}


def add_postfix(file, postfix, extension=None):
    """Adds a postfix to a file before the file extension"""
    if extension is None:
        extension = conf.get_property(fil.get_type(file) + '.default.format')
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
    for tag in key_list:
        if tag in a_dict:
            return a_dict[tag]
    return None


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
            if re.search(r"Picture size \d+x\d+ is invalid", line, re.IGNORECASE):
                current_log_level = logging.WARNING
            elif re.search(r"(error|invalid|failed)", line, re.IGNORECASE):
                current_log_level = logging.ERROR
            elif re.search(r"frame=\s*\d+\s+fps=\s*\d+", line, re.IGNORECASE):
                current_log_level = logging.INFO
                if total_time is not None:
                    m = re.search(r"frame=\s*\d+ fps=[\d\.]+ q=[\d\.]+ size=\s*\d+kB time=(\d+:\d+:\d+\.\d+) bitrate=\s*[\d\.]+kbits\/s dup=\d+ drop=\d+ speed=\s*([\d\.]+)x", line)
                    if m:
                        line += " ETA=" + to_hms_str((total_time - to_seconds(m.group(1))) / float(m.group(2)))
            elif re.search(r"(warning|deprecated|out of range)", line, re.IGNORECASE):
                current_log_level = logging.WARNING
            else:
                current_log_level = logging.DEBUG
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
        if pipe.returncode != 0:
            last_error_line = line if last_error_line is None else last_error_line
            raise subprocess.CalledProcessError(cmd=cmd, output=last_error_line, returncode=pipe.returncode)
        log.logger.info("Successfully completed: %s", cmd)
    except subprocess.CalledProcessError as e:
        log.logger.error("Command: %s failed with return code %d", cmd, e.returncode)
        log.logger.error("%s", e.output)
        raise


def run_ffmpeg(params, duration):
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
        kwargs = remove_nones(vars(parser.parse_args()))
    else:
        kwargs = remove_nones(vars(parser.parse_args(args)))
    # Default debug level is 3 = INFO (0 = CRITICAL, 1 = ERROR, 2 = WARNING, 3 = INFO, 4 = DEBUG)
    set_debug_level(kwargs.pop('debug', 3))
    if opt.Option.WIDTH not in kwargs and opt.Option.HEIGHT not in kwargs and \
            kwargs.get(opt.Option.RESOLUTION, None) is not None:
        kwargs[opt.Option.RESOLUTION] = res.canonical(kwargs[opt.Option.RESOLUTION])
        kwargs[opt.Option.WIDTH], kwargs[opt.Option.HEIGHT] = kwargs[opt.Option.RESOLUTION].split('x', maxsplit=2)
        if kwargs[opt.Option.WIDTH] != '':
            kwargs[opt.Option.WIDTH] = int(kwargs[opt.Option.WIDTH])
        else:
            kwargs[opt.Option.WIDTH] = -1
        if kwargs[opt.Option.HEIGHT] != '':
            kwargs[opt.Option.HEIGHT] = int(kwargs[opt.Option.HEIGHT])
        else:
            kwargs[opt.Option.HEIGHT] = -1
    elif opt.Option.WIDTH not in kwargs and opt.Option.HEIGHT in kwargs:
        kwargs[opt.Option.WIDTH] = -1
    elif opt.Option.WIDTH in kwargs and opt.Option.HEIGHT not in kwargs:
        kwargs[opt.Option.HEIGHT] = -1

    if kwargs.get('timeranges', None) is not None:
        kwargs[opt.Option.START], kwargs[opt.Option.STOP] = kwargs['timeranges'].split(',')[0].split('-')
    log.logger.debug('KW=%s', str(kwargs))
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
        extension = properties.get('default.extension', None)
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
            parms['-' + m.group(1)] = m.group(2)
            cmdline = re.sub(r'^-(\S+)\s+([A-Za-z0-9]\S*)', '', cmdline)
        else:
            # Format -<option>
            m = re.search(r'^-(\S+)\s*', cmdline)
            if m:
                parms['-' + m.group(1)] = None
                cmdline = re.sub(r'^-(\S+)\s*', '', cmdline)
            else:
                found = False
    return parms


def get_ffmpeg_cmdline_param(cmdline, param):
    m = re.search(rf"{param}\s+(\S+)", cmdline)
    if m:
        return m.group(1)
    return None


def get_ffmpeg_cmdline_switch(cmdline, param):
    m = re.search(rf'{param}\s', cmdline)
    if m:
        return True
    return False


def get_ffmpeg_cmdline_vbitrate(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.OptionFfmpeg.VBITRATE)


def get_ffmpeg_cmdline_abitrate(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.OptionFfmpeg.ABITRATE)


def get_ffmpeg_cmdline_vcodec(cmdline):
    for option in [opt.OptionFfmpeg.VCODEC, opt.OptionFfmpeg.VCODEC2, opt.OptionFfmpeg.VCODEC3]:
        v = get_ffmpeg_cmdline_param(cmdline, '-' + option)
        if v is not None:
            return v
    return None


def get_ffmpeg_cmdline_acodec(cmdline):
    for option in [opt.OptionFfmpeg.ACODEC, opt.OptionFfmpeg.ACODEC2, opt.OptionFfmpeg.ACODEC3]:
        v = get_ffmpeg_cmdline_param(cmdline, '-' + option)
        if v is not None:
            return v
    return None


def get_ffmpeg_cmdline_framesize(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.OptionFfmpeg.RESOLUTION)


def get_ffmpeg_cmdline_framerate(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.OptionFfmpeg.FPS)


def get_ffmpeg_cmdline_aspect_ratio(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.OptionFfmpeg.ASPECT)


def get_ffmpeg_cmdline_vfilter(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-vf')


def get_ffmpeg_cmdline_achannels(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.OptionFfmpeg.ACHANNEL)


def get_ffmpeg_cmdline_format(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.OptionFfmpeg.FORMAT)


def get_ffmpeg_cmdline_deinterlace(cmdline):
    return get_ffmpeg_cmdline_switch(cmdline, '-' + opt.OptionFfmpeg.DEINTERLACE)


def get_ffmpeg_cmdline_amute(cmdline):
    return get_ffmpeg_cmdline_switch(cmdline, '-an')


def get_ffmpeg_cmdline_vmute(cmdline):
    return get_ffmpeg_cmdline_switch(cmdline, '-vn')


def get_audio_sample_rate(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-ar')


def get_ffmpeg_cmdline_params(cmdline):
    p = {}
    p[opt.Option.ABITRATE] = get_ffmpeg_cmdline_abitrate(cmdline)
    p[opt.Option.VBITRATE] = get_ffmpeg_cmdline_vbitrate(cmdline)
    p[opt.Option.ACODEC] = get_ffmpeg_cmdline_acodec(cmdline)
    p[opt.Option.VCODEC] = get_ffmpeg_cmdline_vcodec(cmdline)
    p[opt.Option.RESOLUTION] = get_ffmpeg_cmdline_framesize(cmdline)
    p[opt.Option.FPS] = get_ffmpeg_cmdline_framerate(cmdline)
    p[opt.Option.ASPECT] = get_ffmpeg_cmdline_aspect_ratio(cmdline)
    p[opt.Option.VFILTER] = get_ffmpeg_cmdline_vfilter(cmdline)
    p[opt.Option.ACHANNEL] = get_ffmpeg_cmdline_achannels(cmdline)
    p[opt.Option.FORMAT] = get_ffmpeg_cmdline_format(cmdline)
    p[opt.Option.DEINTERLACE] = get_ffmpeg_cmdline_deinterlace(cmdline)
    p['amute'] = get_ffmpeg_cmdline_amute(cmdline)
    p['vmute'] = get_ffmpeg_cmdline_vmute(cmdline)
    return remove_nones(p)


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
