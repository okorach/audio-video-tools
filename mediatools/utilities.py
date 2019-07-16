#!/usr/local/bin/python3

import os
import sys
import re
import platform
import jprops

DEBUG_LEVEL = 0
DRY_RUN = False

FFMPEG_FORMAT_OPTION = 'f'
FFMPEG_SIZE_OPTION = 's'
FFMPEG_VCODEC_OPTION = 'vcodec'
FFMPEG_ACODEC_OPTION = 'acodec'
FFMPEG_VBITRATE_OPTION = 'b:v'
FFMPEG_ABITRATE_OPTION = 'b:a'
FFMPEG_SIZE_OPTION = 's'
FFMPEG_FPS_OPTION = 'r'
FFMPEG_ASPECT_OPTION = 'aspect'
FFMPEG_DEINTERLACE_OPTION = 'deinterlace'
FFMPEG_ACHANNEL_OPTION = 'ac'
FFMPEG_VFILTER_OPTION = 'vf'
FFMPEG_START_OPTION = 'ss'
FFMPEG_STOP_OPTION = 'to'

OPTIONS_MAPPING = { 'format':FFMPEG_FORMAT_OPTION, \
   'vcodec':FFMPEG_VCODEC_OPTION, 'vbitrate':FFMPEG_VBITRATE_OPTION, \
   'acodec':FFMPEG_ACODEC_OPTION, 'abitrate':FFMPEG_ABITRATE_OPTION, \
   'fps':FFMPEG_FPS_OPTION, 'aspect':FFMPEG_ASPECT_OPTION, 'vsize':FFMPEG_SIZE_OPTION, \
   'deinterlace':FFMPEG_DEINTERLACE_OPTION, 'achannel':FFMPEG_ACHANNEL_OPTION, \
   'vfilter':FFMPEG_VFILTER_OPTION, \
   'start': FFMPEG_START_OPTION, 'stop': FFMPEG_STOP_OPTION }

LANGUAGE_MAPPING = { 'fre': 'French', 'eng': 'English'}

OPTIONS_VERBATIM = ['ss', 'to']

if platform.system() == 'Windows':
    DEFAULT_PROPERTIES_FILE = r'E:\Tools\VideoTools.properties'
else:
    DEFAULT_PROPERTIES_FILE = '/Users/Olivier/GitHub/audio-video-tools/VideoTools.properties'

PROPERTIES_FILE = ''
PROPERTIES_VALUES = {}

def filelist(root_dir):
    """Returns and array of all files under a given root directory
    going down into sub directories"""
    fullfilelist = []
    for dir_name, _, file_list in os.walk(root_dir):
        for fname in file_list:
            fullfilelist.append(dir_name + r'\\' + fname)
    return fullfilelist

def audio_filelist(root_dir):
    """Returns and array of all audio files under a given root directory
    going down into sub directories"""
    fullfilelist = []
    for dir_name, _, file_list in os.walk(root_dir):
        for file in file_list:
            if is_audio_file(file):
                fullfilelist.append(dir_name + r'\\' + file)
    return fullfilelist

def video_filelist(root_dir):
    """Returns and array of all video files under a given root directory
    going down into sub directories"""
    fullfilelist = []
    for dir_name, _, file_list in os.walk(root_dir):
        for file in file_list:
            if is_video_file(file):
                fullfilelist.append(dir_name + r'\\' + file)
    return fullfilelist

def image_filelist(root_dir):
    """Returns and array of all audio files under a given root directory
    going down into sub directories"""
    fullfilelist = []
    for dir_name, _, file_list in os.walk(root_dir):
        for file in file_list:
            if is_image_file(file):
                fullfilelist.append(dir_name + r'\\' + file)
    return fullfilelist

def subdir_list(root_dir):
    """Returns and array of all audio files under a given root directory
    going down into sub directories"""
    fullfilelist = []
    for _, _, file_list in os.walk(root_dir):
        for file in file_list:
            if os.path.isdir(file):
                fullfilelist.append(file)
    return fullfilelist

def get_file_extension(filename):
    """Returns a file extension"""
    return re.sub(r'^.*\.', '', filename)

def strip_file_extension(filename):
    """Removes the file extension and returns the string"""
    return re.sub(r'\.[^.]+$', '', filename)

def match_extension(file, regex):
    """Returns boolean, whether the file has a extension that matches the regex (case insensitive)"""
    p = re.compile(regex, re.IGNORECASE)
    return False if re.search(p, file) is None else True

def add_postfix(file, postfix, extension = None):
    """Adds a postfix to a file before the file extension"""
    if extension is None:
        extension = get_file_extension(file)
    return strip_file_extension(file) + r'.' + postfix + r'.' + extension

def automatic_output_file_name(outfile, infile, postfix, extension = None):
    if outfile is not None:
        return outfile
    postfix.replace(':', '-')
    return add_postfix(infile, postfix, extension)

def is_audio_file(file):
    """Returns whether the file has an extension corresponding to audio files"""
    return match_extension(file, r'\.(mp3|ogg|aac|ac3|m4a|ape|flac)$')

def is_video_file(file):
    """Returns whether the file has an extension corresponding to video files"""
    return match_extension(file, r'\.(avi|wmv|mp4|3gp|mpg|mpeg|mkv|ts|mts|m2ts)$')

def is_image_file(file):
    """Returns whether the file has an extension corresponding to images files"""
    return match_extension(file, r'\.(jpg|jpeg|png|gif|svg|raw)$')

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
    debug(2, "Filetype of %s is %s" % (file, filetype))
    return filetype

def get_ffmpeg(props_file = None):
    props = get_media_properties(props_file)
    return props['binaries.ffmpeg']

def get_ffprobe(props_file = None):
    props = get_media_properties(props_file)
    return props['binaries.ffprobe']

def get_first_value(a_dict, key_list):
    for tag in key_list:
        if tag in a_dict:
            return a_dict[tag]
    return None

def run_os_cmd(cmd):
    if DEBUG_LEVEL < 2:
        cmd = cmd + " 1>>mediatools.log 2>&1"
    debug(1, "Running: %s" % cmd)
    os.system(cmd)

def run_ffmpeg(params):
    cmd = "%s -y %s" % (get_ffmpeg(), params)
    if is_dry_run():
        print(cmd, end='\n')
    else:
        run_os_cmd(cmd)

def build_ffmpeg_file_list(file_list):
    s = ''
    for f in file_list:
        s = s + ' -i "%s"' % f
    return s

def build_ffmpeg_complex_prep(file_list):
    s = ''
    for i in range(len(file_list)+1):
        s = s + "[%d]scale=iw:-1:flags=lanczos[pip%d]; " % (i, i)
    return s

def get_media_properties(props_file = None):
    """Returns all properties found in the properties file as dictionary"""
    global DEFAULT_PROPERTIES_FILE
    global PROPERTIES_FILE
    global PROPERTIES_VALUES
    if props_file is None:
        props_file = DEFAULT_PROPERTIES_FILE
    if props_file == PROPERTIES_FILE and PROPERTIES_VALUES != {}:
        return PROPERTIES_VALUES
    PROPERTIES_FILE = props_file
    try:
        with open(props_file) as fp:
            PROPERTIES_VALUES = jprops.load_properties(fp)
    except FileNotFoundError:
        PROPERTIES_VALUES['binaries.ffmpeg'] = 'ffmpeg'
        PROPERTIES_VALUES['binaries.ffprobe'] = 'ffprobe'
    return PROPERTIES_VALUES

def to_hms(seconds):
    s = float(seconds)
    hours = int(s)//3600
    minutes = int(s)//60 - hours*60
    secs = s - hours*3600 - minutes*60
    return (hours, minutes, secs)

def to_hms_str(seconds):
    hours, minutes, secs = to_hms(seconds)
    return "%d:%02d:%06.3f" % (hours, minutes, secs)

def set_debug_level(level):
    global DEBUG_LEVEL
    if level is None:
        level = 0
    DEBUG_LEVEL = int(level)
    debug(1, "Set debug level to %d" % DEBUG_LEVEL)

def set_dry_run(dry_run):
    global DRY_RUN
    DRY_RUN = dry_run
    debug(1, "Set dry run to %s" % str(dry_run))

def is_dry_run():
    global DRY_RUN
    return DRY_RUN

def delete_files(*args):
    if is_dry_run():
        return
    for f in args:
        os.remove(f)

def debug(level, string):
    global DEBUG_LEVEL
    if level <= DEBUG_LEVEL:
        print("DEBUG | %d | %s" % (level, string))

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
    new_options = kwargs.copy()
    for key in ['inputfile', 'outputfile', 'profile']:
        new_options.pop(key, None)
    return new_options

def check_environment(kwargs):
    set_debug_level(kwargs.pop('debug', 0))
    set_dry_run(kwargs.pop('dry_run', 'false'))

def get_profile_extension(profile, properties = None):
    if properties is None:
        properties = get_media_properties()
    extension = properties.get(profile + '.extension', None)
    if extension is None:
        extension = properties.get('default.extension', None)
    return extension

def get_profile_params(profile):
    props = get_media_properties()
    return get_cmdline_params(props[profile +'.cmdline'])

def get_cmdline_params(cmdline):
    """Returns a dictionary of all parameters found on input string command line
    Parameters can be of the format -<option> <value> or -<option>"""
    found = True
    parms = dict()
    while found:
        cmdline = re.sub(r'^\s+', '', cmdline) # Remove heading spaces
        m = re.search(r'^-(\S+)\s+([A-Za-z0-9]\S*)', cmdline) # Format -<option> <value>
        if m:
            parms[m.group(1)] = m.group(2)
            #print("Found " + m.group(1) + " --> " + m.group(2))
            cmdline = re.sub(r'^-(\S+)\s+([A-Za-z0-9]\S*)', '', cmdline)
        else:
            m = re.search(r'^-(\S+)\s*', cmdline)  # Format -<option>
            if m:
                parms[m.group(1)] = None
                cmdline = re.sub(r'^-(\S+)\s*', '', cmdline)
            else:
                found = False
    return parms
