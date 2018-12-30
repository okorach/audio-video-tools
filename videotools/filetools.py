#!python3
 
import os
import re
import jprops

debug_level = 0

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
            if (is_audio_file(file)):
                fullfilelist.append(dir_name + r'\\' + file)
    return fullfilelist

def video_filelist(root_dir):
    """Returns and array of all video files under a given root directory
    going down into sub directories"""
    fullfilelist = []
    for dir_name, _, file_list in os.walk(root_dir):
        for file in file_list:
            if (is_video_file(file)):
                fullfilelist.append(dir_name + r'\\' + file)
    return fullfilelist

def image_filelist(root_dir):
    """Returns and array of all audio files under a given root directory
    going down into sub directories"""
    fullfilelist = []
    for dir_name, _, file_list in os.walk(root_dir):
        for file in file_list:
            if (is_image_file(file)):
                fullfilelist.append(dir_name + r'\\' + file)
    return fullfilelist

def subdir_list(root_dir):
    """Returns and array of all audio files under a given root directory
    going down into sub directories"""
    fullfilelist = []
    for _, _, file_list in os.walk(root_dir):
        for file in file_list:
            if (os.path.isdir(file)):
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

def is_audio_file(file):
    """Returns whether the file has an extension corresponding to audio files"""
    return match_extension(file,  r'\.(mp3|ogg|aac|ac3|m4a|ape)$')

def is_video_file(file):
    """Returns whether the file has an extension corresponding to video files"""
    return match_extension(file,  r'\.(avi|wmv|mp4|3gp|mpg|mpeg|mkv|ts|mts|m2ts)$')

def is_image_file(file):
    """Returns whether the file has an extension corresponding to images files"""
    return match_extension(file,  r'\.(jpg|jpeg|png|gif|svg|raw)$')

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
    debug(2, "Fietype of %s is %s" % (file, filetype))
    return filetype

def get_properties(props_file):
    """Returns all properties found in the properties file as dictionary"""
    with open(props_file) as fp:
        properties = jprops.load_properties(fp)
    return properties

def to_k(value):
    return int(value)/1024

def to_m(value):
    return int(value)/1024/1024

def set_debug_level(level):
    global debug_level
    if level is None:
        level = 0
    debug_level = int(level)

def debug(level, string):
    global debug_level
    if level <= debug_level:
        print(string)