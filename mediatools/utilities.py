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
import re
import logging
import argparse
import pathlib
import subprocess
import shlex
import mediatools.options as opt
import mediatools.resolution as res
import mediatools.media_config as conf

DEBUG_LEVEL = 0
DRY_RUN = False
logger = logging.getLogger('mediatools')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = logging.FileHandler('mediatools.log')
# fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)
logger.addHandler(fh)
logger.addHandler(ch)
fh.setFormatter(formatter)
ch.setFormatter(formatter)


class MediaType:
    AUDIO_FILE = 1
    VIDEO_FILE = 2
    IMAGE_FILE = 3
    FILE_EXTENSIONS = {
        AUDIO_FILE: r'\.(mp3|ogg|aac|ac3|m4a|ape|flac)$',
        VIDEO_FILE: r'\.(avi|wmv|mp4|3gp|mpg|mpeg|mkv|ts|mts|m2ts|mov)$',
        IMAGE_FILE: r'\.(jpg|jpeg|png|gif|svg|raw)$'
    }


LANGUAGE_MAPPING = {'fre': 'French', 'eng': 'English'}

OPTIONS_VERBATIM = ['ss', 'to']

config_props = os.path.realpath(__file__).split(os.path.sep)
config_props.pop()
config_props.pop()
config_props.append("media-tools.properties")
DEFAULT_PROPERTIES_FILE = os.path.sep.join(config_props)
logger.debug("Default properties file = %s", DEFAULT_PROPERTIES_FILE)

PROPERTIES_FILE = ''
PROPERTIES_VALUES = {}


def set_logger(name):
    global logger
    logger = logging.getLogger(name)
    new_fh = logging.FileHandler(name + '.log')
    new_ch = logging.StreamHandler()
    logger.addHandler(new_fh)
    logger.addHandler(new_ch)
    new_fh.setFormatter(formatter)
    new_ch.setFormatter(formatter)


def dir_list(root_dir, recurse=False, file_type=None):
    """Returns and array of all files under a given root directory
    going down into sub directories"""
    logger.info("Searching files in %s (recurse=%s)", root_dir, str(recurse))
    files = []
    # 3 params are r=root, _=directories, f = files
    for r, _, f in os.walk(root_dir):
        for file in f:
            if os.path.isdir(file) and recurse:
                files.append(dir_list(file, recurse=recurse, file_type=file_type))
            elif __is_type_file(os.path.join(r, file), file_type):
                files.append(os.path.join(r, file))
    logger.info("Found %d files in %s", len(files), root_dir)
    return files


def file_list(*args, file_type=None, recurse=False):
    logger.debug("Searching files in %s", str(args))
    files = []
    for arg in args:
        logger.debug("Check file %s", str(arg))
        if os.path.isdir(arg):
            files.extend(dir_list(arg, file_type=file_type, recurse=recurse))
        elif file_type is None or __is_type_file(arg, file_type):
            files.append(arg)
    return files


def get_file_extension(filename):
    """Returns a file extension"""
    return filename.split('.').pop()


def strip_file_extension(filename):
    """Removes the file extension and returns the string"""
    return '.'.join(filename.split('.')[:-1])


def __match_extension__(file, regex):
    """Returns boolean, whether the file has a extension that matches the regex (case insensitive)"""
    ext = '.' + get_file_extension(file)
    p = re.compile(regex, re.IGNORECASE)
    return not re.search(p, ext) is None


def add_postfix(file, postfix, extension=None):
    """Adds a postfix to a file before the file extension"""
    if extension is None:
        extension = conf.get_property(get_file_type(file) + '.default.format')
    if extension is None:
        extension = get_file_extension(file)
    return strip_file_extension(file) + r'.' + postfix + r'.' + extension


def automatic_output_file_name(outfile, infile, postfix, extension=None):
    if outfile is not None:
        return outfile
    postfix.replace(':', '-')
    return add_postfix(infile, postfix, extension)


def __is_type_file(file, type_of_media):
    return type_of_media is None or (
        os.path.isfile(file) and __match_extension__(file, MediaType.FILE_EXTENSIONS[type_of_media]))


def is_audio_file(file):
    return __is_type_file(file, MediaType.AUDIO_FILE)


def is_video_file(file):
    return __is_type_file(file, MediaType.VIDEO_FILE)


def is_image_file(file):
    return __is_type_file(file, MediaType.IMAGE_FILE)


def is_media_file(file):
    """Returns whether the file has an extension corresponding to media (audio/video/image) files"""
    return is_audio_file(file) or is_image_file(file) or is_video_file(file)


def get_file_type(file):
    if is_audio_file(file):
        filetype = 'audio'
    elif is_video_file(file):
        filetype = 'video'
    elif is_image_file(file):
        filetype = 'image'
    else:
        filetype = 'unknown'
    logger.debug("Filetype of %s is %s", file, filetype)
    return filetype


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


def run_os_cmd(cmd):
    logger.info("Running: %s", cmd)
    try:
        last_error = None
        args = shlex.split(cmd)
        pipe = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, bufsize=1)
        line = pipe.stdout.readline().rstrip()
        while line:
            if re.search(r"Picture size \d+x\d+ is invalid", line, re.IGNORECASE):
                last_error = line
            elif re.search(r"(error|invalid|failed)", line, re.IGNORECASE):
                logger.error(line)
            elif re.search(r"frame=\s*(\d+)\s+fps=\s*(\d+)", line, re.IGNORECASE):
                logger.info(line)
            elif re.search(r"(warning|deprecated|out of range)", line, re.IGNORECASE):
                logger.warning(line)
            else:
                logger.debug(line)
            line = pipe.stdout.readline().rstrip()
        outs, errs = pipe.communicate()
        logger.debug("Return code = %d", pipe.returncode)
        if pipe.returncode != 0:
            last_error = line if last_error is None else last_error
            raise subprocess.CalledProcessError(cmd=cmd, output=last_error, returncode=pipe.returncode)
        logger.info("Successfully completed: %s", cmd)
    except subprocess.CalledProcessError as e:
        logger.error("Command: %s failed with return code %d", cmd, e.returncode)
        logger.error("%s", e.output)
        raise


def run_ffmpeg(params):
    quot = '"' if platform.system() == 'Windows' else ""
    cmd = '{0}{1}{0} -y {2}'.format(quot, get_ffmpeg(), params)
    run_os_cmd(cmd)


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
        logger.debug("Props = %s", str(PROPERTIES_VALUES))
    return PROPERTIES_VALUES


def get_conf_property(prop):
    global PROPERTIES_VALUES
    if not PROPERTIES_VALUES:
        get_media_properties()
    return PROPERTIES_VALUES[prop]


def to_hms(seconds, fmt='tuple'):
    try:
        s = int(seconds)
        hours = s // 3600
        minutes = s // 60 - hours * 60
        secs = float(seconds) - hours * 3600 - minutes * 60
        if fmt == 'string':
            return "%02d:%02d:%04.1f" % (hours, minutes, secs)
        else:
            return (hours, minutes, secs)
    except TypeError:
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
    return "%d:%02d:%06.3f" % (hours, minutes, secs)


def get_logging_level(intlevel):
    if intlevel >= 2:
        lvl = logging.DEBUG
    elif intlevel >= 1:
        lvl = logging.INFO
    elif intlevel >= 0:
        lvl = logging.ERROR
    else:
        lvl = logging.CRITICAL
    return lvl


def json_fmt(json_data):
    return json.dumps(json_data, sort_keys=True, indent=3, separators=(',', ': '))


def set_debug_level(level):
    global DEBUG_LEVEL
    DEBUG_LEVEL = 0 if level is None else int(level)
    logger.setLevel(get_logging_level(DEBUG_LEVEL))
    logger.info("Set debug level to %d", DEBUG_LEVEL)


def delete_files(*args):
    for f in args:
        logger.debug("Deleting file %s", f)
        os.remove(f)


def get_common_args(executable, desc):
    """Parses options common to all media encoding scripts"""

    set_logger(executable)

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-i', '--inputfile', required=True, help='Input file or directory to encode')
    parser.add_argument('-o', '--outputfile', required=False, help='Output file or directory')

    parser.add_argument('--' + opt.Option.WIDTH, required=False, type=int, help='width of video/image')
    parser.add_argument('--' + opt.Option.HEIGHT, required=False, type=int, help='height of video/image')
    parser.add_argument('-s', '--' + opt.Option.SIZE, required=False, help='Media size HxW for videos and images')

    parser.add_argument('--aspect', required=False, help='Aspect Ratio eg 16:9, 4:3, 1.5 ...')

    parser.add_argument('-g', '--debug', required=False, help='Debug level')

    return parser


def remove_nones(p):
    return dict((k, v) for k, v in p.items() if v is not None)


def parse_media_args(parser):
    kwargs = remove_nones(vars(parser.parse_args()))
    set_debug_level(kwargs.pop('debug', 1))
    if opt.Option.WIDTH not in kwargs and opt.Option.HEIGHT not in kwargs and \
            kwargs.get(opt.Option.SIZE, None) is not None:
        kwargs[opt.Option.SIZE] = res.canonical(kwargs[opt.Option.SIZE])
        kwargs[opt.Option.WIDTH], kwargs[opt.Option.HEIGHT] = kwargs[opt.Option.SIZE].split('x', maxsplit=2)
        if kwargs[opt.Option.WIDTH] == '':
            kwargs[opt.Option.WIDTH] = -1
        else:
            kwargs[opt.Option.WIDTH] = int(kwargs[opt.Option.WIDTH])
        if kwargs[opt.Option.HEIGHT] == '':
            kwargs[opt.Option.HEIGHT] = -1
        else:
            kwargs[opt.Option.HEIGHT] = int(kwargs[opt.Option.HEIGHT])
    if kwargs.get('timeranges', None) is not None:
        kwargs[opt.Option.START], kwargs[opt.Option.STOP] = kwargs['timeranges'].split(',')[0].split('-')
    logger.debug('KW=%s', str(kwargs))
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
    props = get_media_properties()
    return get_cmdline_params(props[profile + '.cmdline'])


def get_cmdline_params(cmdline):
    """Returns a dictionary of all parameters found on input string command line
    Parameters can be of the format -<option> <value> or -<option>"""
    found = True
    parms = dict()
    while found:
        # Remove heading spaces
        cmdline = re.sub(r'^\s+', '', cmdline)
        # Format -<option> <value>
        m = re.search(r'^-(\S+)\s+([A-Za-z0-9]\S*)', cmdline)
        if m:
            parms[m.group(1)] = m.group(2)
            cmdline = re.sub(r'^-(\S+)\s+([A-Za-z0-9]\S*)', '', cmdline)
        else:
            # Format -<option>
            m = re.search(r'^-(\S+)\s*', cmdline)
            if m:
                parms[m.group(1)] = None
                cmdline = re.sub(r'^-(\S+)\s*', '', cmdline)
            else:
                found = False
    return parms


def int_split(string, separator):
    a, b = string.split(separator)
    return [int(a), int(b)]


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
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.OptionFfmpeg.SIZE)


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
    p[opt.Option.SIZE] = get_ffmpeg_cmdline_framesize(cmdline)
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
    return dict([(v, k) for k, v in p.items()])


def dict2str(options):
    cmd = ''
    for k in options:
        if options[k] is None or options[k] is False:
            continue
        if options[k] is True:
            fmt = " -{0}".format(k)
        else:
            fmt = " -{0} {1}".format(k, options[k])
        cmd += fmt
    logger.debug("cmd options = %s", cmd)
    return cmd


def find_key(hashlist, keylist):
    for key in keylist:
        if key not in hashlist:
            continue
        return hashlist[key]

    logger.warning("No key %s found in %s", str(keylist), str(hashlist))
    return None


def percent_or_absolute(x, reference=1):
    if isinstance(x, str) and re.match(r'-?\d+(.\d+)?%', x):
        return float(x[:-1]) * reference / 100
    return x


def generated_file(filename):
    logger.info("Generated %s", filename)
    print("Generated {}".format(filename))


def package_home():
    return pathlib.Path(__file__).parent
