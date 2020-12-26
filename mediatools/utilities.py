#!python3
#
# media-tools
# Copyright (C) 2019-2020 Olivier Korach
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
import json
import re
import logging
import subprocess
import shlex
import mediatools.options as opt

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
    files = []
    # 3 params are r=root, _=directories, f = files
    for r, _, f in os.walk(root_dir):
        for file in f:
            if os.path.isdir(file) and recurse:
                files.append(dir_list(file))
            elif __is_type_file(file, file_type):
                files.append(os.path.join(r, file))
    return files


def file_list(*args):
    logger.debug("Searching files in %s", str(args))
    files = []
    for arg in args:
        logger.debug("Check file %s", str(arg))
        if os.path.isdir(arg):
            files.extend(dir_list(arg))
        else:
            files.append(arg)
    return files


def file_list_by_type(root_dir, file_type):
    """Returns and array of all files of a given typeunder a given root directory
    going down into sub directories"""
    files = []
    for file in dir_list(root_dir):
        if __is_type_file(file, file_type):
            files.append(file)
    return files


def audio_filelist(root_dir):
    return file_list_by_type(root_dir, MediaType.AUDIO_FILE)


def video_filelist(root_dir):
    return file_list_by_type(root_dir, MediaType.VIDEO_FILE)


def image_filelist(root_dir):
    return file_list_by_type(root_dir, MediaType.IMAGE_FILE)


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
        args = shlex.split(cmd)
        pipe = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        line = pipe.stdout.readline()
        while line:
            logger.debug(line.decode("utf-8").rstrip())
            line = pipe.stdout.readline()
        logger.info("Successfully completed: %s", cmd)
    except subprocess.CalledProcessError as e:
        logger.error("%s", e.output)
        logger.error("Command: %s failed with code %d", cmd, e.returncode)
        raise OSError(e.returncode)


def run_ffmpeg(params):
    cmd = "%s -y %s" % (get_ffmpeg(), params)
    if is_dry_run():
        logger.info("DRY RUN: %s", cmd)
    else:
        run_os_cmd(cmd)


def build_ffmpeg_file_list(file_list):
    s = ''
    for f in file_list:
        s += ' -i "%s"' % f
    return s


def build_ffmpeg_complex_prep(file_list):
    s = ''
    for i in range(len(file_list) + 1):
        s += "[%d]scale=iw:-1:flags=lanczos[pip%d]; " % (i, i)
    return s


def get_media_properties():
    """Returns all properties found in the properties file as dictionary"""
    import mediatools.media_config as mediaconf
    global PROPERTIES_VALUES
    if not PROPERTIES_VALUES:
        PROPERTIES_VALUES = mediaconf.load()
        logger.debug("Props = %s", str(PROPERTIES_VALUES))
    return PROPERTIES_VALUES


def get_conf_property(prop):
    global PROPERTIES_VALUES
    if not PROPERTIES_VALUES:
        get_media_properties()
    return PROPERTIES_VALUES[prop]


def to_hms(seconds):
    try:
        s = int(seconds)
        hours = s // 3600
        minutes = s // 60 - hours * 60
        secs = float(seconds) - hours * 3600 - minutes * 60
        return (hours, minutes, secs)
    except TypeError:
        return (0, 0, 0)


def to_seconds(hms):
    a = [float(x) for x in hms.split(':')]
    return a[0] * 3600 + a[1] * 60 + a[2]


def difftime(start, stop):
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


def set_dry_run(dry_run):
    global DRY_RUN
    DRY_RUN = dry_run
    logger.info("Set dry run to %s", str(dry_run))


def is_dry_run():
    return DRY_RUN


def delete_files(*args):
    if is_dry_run():
        return
    for f in args:
        logger.debug("Deleting file %s", f)
        os.remove(f)


def parse_common_args(desc):
    """Parses options common to all media encoding scripts"""
    try:
        import argparse
    except ImportError:
        if sys.version_info < (2, 7, 0):
            print("""Error: You are running an old version of python. Two options to fix the problem
                   Option 1: Upgrade to python version >= 2.7
                   Option 2: Install argparse library for the current python version
                             See: https://pypi.python.org/pypi/argparse""")
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-i', '--inputfile', required=True, help='Input file or directory to encode')
    parser.add_argument('-o', '--outputfile', required=False, help='Output file or directory')

    parser.add_argument('--framesize', required=False, help='Media size HxW for videos and images')
    parser.add_argument('--framewidth', required=False, help='Media width for videos and images')

    parser.add_argument('--aspect', required=False, help='Aspect Ratio eg 16:9, 4:3, 1.5 ...')

    parser.add_argument('--croph', required=False, help='Horizontal cropping top and bottom')
    parser.add_argument('--cropv', required=False, help='Vertical cropping left and right')

    parser.add_argument('--croptop', required=False, help='Croptop')
    parser.add_argument('--cropleft', required=False, help='Cropleft')
    parser.add_argument('--cropbottom', required=False, help='Croptop')
    parser.add_argument('--cropright', required=False, help='Cropleft')

    parser.add_argument('--dry_run', required=False, default=False, help='Only display ffmpeg command, don\'t run it')
    parser.add_argument('-g', '--debug', required=False, help='Debug level')

    return parser


def cleanup_options(kwargs):
    new_options = remove_nones(kwargs)
    for key in ['inputfile', 'outputfile', 'profile']:
        new_options.pop(key, None)
    return new_options


def check_environment(kwargs):
    set_debug_level(kwargs.pop('debug', 0))
    set_dry_run(kwargs.pop('dry_run', 'false'))


def get_profile_extension(profile, properties=None):
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
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.ff.VBITRATE)


def get_ffmpeg_cmdline_abitrate(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.ff.ABITRATE)


def get_ffmpeg_cmdline_vcodec(cmdline):
    for option in [opt.ff.VCODEC, opt.ff.VCODEC2, opt.ff.VCODEC3]:
        v = get_ffmpeg_cmdline_param(cmdline, '-' + option)
        if v is not None:
            return v
    return None


def get_ffmpeg_cmdline_acodec(cmdline):
    for option in [opt.ff.ACODEC, opt.ff.ACODEC2, opt.ff.ACODEC3]:
        v = get_ffmpeg_cmdline_param(cmdline, '-' + option)
        if v is not None:
            return v
    return None


def get_ffmpeg_cmdline_framesize(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.ff.SIZE)


def get_ffmpeg_cmdline_framerate(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.ff.FPS)


def get_ffmpeg_cmdline_aspect_ratio(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.ff.ASPECT)


def get_ffmpeg_cmdline_vfilter(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-vf')


def get_ffmpeg_cmdline_achannels(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.ff.ACHANNEL)


def get_ffmpeg_cmdline_format(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-' + opt.ff.FORMAT)


def get_ffmpeg_cmdline_deinterlace(cmdline):
    return get_ffmpeg_cmdline_switch(cmdline, '-' + opt.ff.DEINTERLACE)


def get_ffmpeg_cmdline_amute(cmdline):
    return get_ffmpeg_cmdline_switch(cmdline, '-an')


def get_ffmpeg_cmdline_vmute(cmdline):
    return get_ffmpeg_cmdline_switch(cmdline, '-vn')


def get_audio_sample_rate(cmdline):
    return get_ffmpeg_cmdline_param(cmdline, '-ar')


def get_ffmpeg_cmdline_params(cmdline):
    p = {}
    p[opt.media.ABITRATE] = get_ffmpeg_cmdline_abitrate(cmdline)
    p[opt.media.VBITRATE] = get_ffmpeg_cmdline_vbitrate(cmdline)
    p[opt.media.ACODEC] = get_ffmpeg_cmdline_acodec(cmdline)
    p[opt.media.VCODEC] = get_ffmpeg_cmdline_vcodec(cmdline)
    p[opt.media.SIZE] = get_ffmpeg_cmdline_framesize(cmdline)
    p[opt.media.FPS] = get_ffmpeg_cmdline_framerate(cmdline)
    p[opt.media.ASPECT] = get_ffmpeg_cmdline_aspect_ratio(cmdline)
    p[opt.media.VFILTER] = get_ffmpeg_cmdline_vfilter(cmdline)
    p[opt.media.ACHANNEL] = get_ffmpeg_cmdline_achannels(cmdline)
    p[opt.media.FORMAT] = get_ffmpeg_cmdline_format(cmdline)
    p[opt.media.DEINTERLACE] = get_ffmpeg_cmdline_deinterlace(cmdline)
    p['amute'] = get_ffmpeg_cmdline_amute(cmdline)
    p['vmute'] = get_ffmpeg_cmdline_vmute(cmdline)
    return remove_nones(p)


def remove_nones(p):
    return dict((k, v) for k, v in p.items() if v is not None)


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
