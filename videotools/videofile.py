#!python3

import sys
import ffmpeg
import re
import os
import jprops
import shutil

class FileTypeError(Exception):
    pass

PROPERTIES_FILE = r'E:\Tools\VideoTools.properties'
FFMPEG = r'E:\Tools\VideoTools.properties'

class EncodeSpecs:
    def __init__(self):
        self.vcodec = 'libx264'
        self.acodec = 'libvo_aacenc'
        self.vbitrate = '2048k'
        self.abitrate = '128k'

    def set_vcodec(self, vcodec):
        self.vcodec = vcodec

    def set_acodec(self, acodec):
        self.acodec = acodec
    
    def set_vbitrate(self, bitrate):
        self.vbitrate = bitrate

    def set_abitrate(self, bitrate):
        self.abitrate = bitrate
    
    def set_format(self, fmt):
        self.format = fmt

class VideoFile:
    def __init__(self, filename):
        self.filename = filename
        self.stream = ffmpeg.input(filename)

    def set_profile(self, profile):
        self.profile = profile

    def set_fps(self, fps):
        self.stream = ffmpeg.filter_(self.stream, 'fps', fps=fps, round='up')
    
    def encode(self, target_file, profile):
        # stream = ffmpeg.input(self.filename)
        self.stream = ffmpeg.output(self.stream, target_file, acodec='libvo_aacenc', vcodec='libx264', f='mp4', vr='2048k', ar='128k' )
        self.stream = ffmpeg.overwrite_output(self.stream)

        try:
            ffmpeg.run(self.stream)
        except ffmpeg.Error as e:
            print(e.stderr, file=sys.stderr)
            sys.exit(1)
    
    def aspect(self, aspect_ratio):
        self.stream = ffmpeg.filter_(self.stream, 'fps', aspect=aspect_ratio)

    def scale(self, scale):
        self.stream = ffmpeg.filter_(self.stream, 'scale', size=scale)

    def crop(self, x, y, h, w):
        self.stream = ffmpeg.crop(self.stream, x, y, h, w)

    def get_metadata(self):
        return ffmpeg.probe(self.filename)

    def set_author(self, author):
        self.author = author

    def get_author(self):
        return self.author

    def set_copyright(self, copyright):
        self.copyright = copyright

    def get_copyright(self):
        return self.copyright


def get_size(cmdline):
    m = re.search(r'-s\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_video_codec(cmdline):
    m = re.search(r'-vcodec\s+(\S+)', cmdline)
    if m:
        return m.group(1) 
    m = re.search(r'-c:v\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_audio_codec(cmdline):
    m = re.search(r'-acodec\s+(\S+)', cmdline)
    if m:
        return m.group(1) 
    m = re.search(r'-c:a\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_format(cmdline):
    m = re.search(r'-f\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_audio_bitrate(cmdline):
    m = re.search(r'-ab\s+(\S+)', cmdline)
    if m:
        return m.group(1) 
    m = re.search(r'-b:a\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_video_bitrate(cmdline):
    m = re.search(r'-vb\s+(\S+)', cmdline)
    if m:
        return m.group(1) 
    m = re.search(r'-b:v\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_aspect_ratio(cmdline):
    m = re.search(r'-aspect\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_frame_rate(cmdline):
    m = re.search(r'-r\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_params(cmdline):
    found = True
    parms = dict()
    while (found):
        cmdline = re.sub(r'^\s+', '', cmdline) # Remove heading spaces
        m = re.search(r'^-(\S+)\s+([A-Za-z0-9]\S*)', cmdline) # Format -<option> <value>
        if m:
            parms[m.group(1)] = m.group(2)
            print("Found " + m.group(1) + " --> " + m.group(2))
            cmdline = re.sub(r'^-(\S+)\s+([A-Za-z0-9]\S*)', '', cmdline)
        else:
            m = re.search(r'^-(\S+)\s*', cmdline)  # Format -<option>
            if m:
                parms[m.group(1)] = None
                cmdline = re.sub(r'^-(\S+)\s*', '', cmdline)
            else:
                found = False
    return parms

def get_file_extension(filename):
    return re.sub(r'^.*\.', '', filename)
  
def strip_file_extension(filename):
    return re.sub(r'\.[^.]+$', '', filename)

def get_extension(profile):
    with open(PROPERTIES_FILE) as fp:
        properties = jprops.load_properties(fp)
    try:
        extension = properties[profile + '.extension']
    except KeyError:
        extension = properties['default.extension']
    return extension

def build_target_file(source_file, profile, properties):
    try:
        extension = properties[profile + '.extension']
    except KeyError:
        extension = properties['default.extension']
    
    # Strip extension from source file
    target_file = strip_file_extension(source_file) + r'.' + profile + r'.' + extension
    return target_file


def encode(source_file, target_file, profile):
    with open(PROPERTIES_FILE) as fp:
        properties = jprops.load_properties(fp)

    myprop = properties[profile + '.cmdline']
    if target_file is None:
        target_file = build_target_file(source_file, profile, properties)

    stream = ffmpeg.input(source_file)
    parms = get_params(myprop)
    #stream = ffmpeg.output(stream, target_file, acodec=getAudioCodec(myprop), ac=2, an=None, vcodec=getVideoCodec(myprop),  f=getFormat(myprop), aspect=getAspectRatio(myprop), s=getSize(myprop), r=getFrameRate(myprop)  )
    stream = ffmpeg.output(stream, target_file, **parms  )
    # -qscale:v 3  is **{'qscale:v': 3} 
    stream = ffmpeg.overwrite_output(stream)
    # print(ffmpeg.get_args(stream))
    print (source_file + ' --> ' + target_file)
    try:
        ffmpeg.run(stream, cmd=properties['binaries.ffmpeg'], capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        print(e.stderr, file=sys.stderr)
        sys.exit(1)

def get_properties():
    try:
        with open(PROPERTIES_FILE) as fp:
            properties = jprops.load_properties(fp)
    except FileNotFoundError:
        properties['binaries.ffmpeg'] = 'ffmpeg'
        properties['binaries.ffprobe'] = 'ffprobe'
    return properties

def encode_album_art(source_file, album_art_file):
    profile = 'album_art' # For the future, we'll use the cmd line associated to the profile in the config file
    properties = get_properties()
    target_file = strip_file_extension(source_file) + '.album_art.' + get_file_extension(source_file)

    # ffmpeg -i %1 -i %2 -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)" %1.mp3
    cmd = properties['binaries.ffmpeg'] + ' -i "' + source_file + '" -i "' + album_art_file \
        + '" -map 0:0 -map 1:0 -c copy -id3v2_version 3 ' \
        + ' -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)" ' \
        + '"' + target_file + '"'
    print("Running %s" % cmd)
    os.system(cmd)
    shutil.copy(target_file, source_file)
    os.remove(target_file)

def rescale(in_file, width, height, out_file = None):
    properties = get_properties()
    if out_file is None:
        out_file = strip_file_extension(in_file) + '.' + str(width) + 'x' + str(height) + '.' + get_file_extension(in_file)
    stream = ffmpeg.input(in_file)
    stream = ffmpeg.filter_(stream, 'scale', size=str(width) + ':' + str(height))
    stream = ffmpeg.output(stream, out_file)
    ffmpeg.run(stream, cmd=properties['binaries.ffmpeg'], capture_stdout=True, capture_stderr=True)
    return out_file

def get_file_specs(file):
    properties = get_properties()
    probe = None
    if is_media_file(file):
        try:
            specs = ffmpeg.probe(file, cmd=properties['binaries.ffprobe'])
        except AttributeError:
            print (dir(ffmpeg))
    else:
        raise FileTypeError('File %s is neither video, audio nor image file' % file)

    file_type = specs['format']['format_name']
    myspecs = dict()
    myspecs['filename'] = specs['format']['filename']
    myspecs['filesize'] = specs['format']['size']
    #if file_type == 'image2':
    if is_image_file(file):
        myspecs['type'] = 'image'
    #elif file_type == 'mp3' or file_type == 'aac':
    elif is_audio_file(file):
        myspecs['type'] = 'audio'
        myspecs['format'] = specs['streams'][0]['codec_name']
    #elif re.search(r'mp4', file_type) is not None:
    elif is_video_file(file):
        myspecs['type'] = 'video'
        myspecs['format'] = get_file_extension(file)

    for stream in specs['streams']:
        try:
            if myspecs['type'] == 'image':
                myspecs['image_codec'] = stream['codec_name']
                myspecs['width'] = stream['width']
                myspecs['height'] = stream['height']
                myspecs['format'] = stream['codec_name']
            elif myspecs['type'] == 'video' and stream['codec_type'] == 'video':
                myspecs['type'] = 'video'
                myspecs['video_codec'] = stream['codec_name']
                myspecs['video_bitrate'] = stream['bit_rate']
                myspecs['width'] = stream['width']
                myspecs['height'] = stream['height']
                myspecs['duration'] = stream['duration']
                myspecs['duration_hms'] = to_hms_str(stream['duration'])
                myspecs['aspect_ratio'] = stream['display_aspect_ratio']
                myspecs['fps'] = stream['r_frame_rate']
            elif (myspecs['type'] == 'audio' or myspecs['type'] == 'video') and stream['codec_type'] == 'audio':
                myspecs['audio_codec'] = stream['codec_name']
                myspecs['sample_rate'] = stream['sample_rate']
                myspecs['duration'] = stream['duration']
                myspecs['duration_hms'] = to_hms_str(stream['duration'])
                myspecs['audio_bitrate'] = stream['bit_rate']
        except KeyError as e:
            #print("Stream %s has no key %s" % (str(stream), e.args[0]))
            #print(specs)
            pass
    return myspecs

def filelist(root_dir):
    fullfilelist = []
    for dir_name, _, file_list in os.walk(root_dir):
        for fname in file_list:
            fullfilelist.append(dir_name + r'\\' + fname)
    return fullfilelist

def match_extension(file, regex):
    p = re.compile(regex, re.IGNORECASE)
    if re.search(p, file) is None:
        return False
    else:
        return True

def is_audio_file(file):
    return match_extension(file,  r'\.(mp3|ogg|aac|ac3|m4a|ape)$')

def is_video_file(file):
    return match_extension(file,  r'\.(avi|wmv|mp4|3gp|mpg|mpeg|mkv|ts|mts|m2ts)$')

def is_image_file(file):
    return match_extension(file,  r'\.(jpg|jpeg|png)$')

def is_media_file(file):
    return is_audio_file(file) or is_image_file(file) or is_video_file(file)

def to_hms(seconds):
    s = float(seconds)
    hours = int(s)//3600
    minutes = int(s)//60 - hours*60
    secs = s - hours*3600 - minutes*60
    return (hours, minutes, secs)
    
def to_hms_str(seconds):
    hours, minutes, secs = to_hms(seconds)
    return "%d:%02d:%06.3f" % (hours, minutes, secs)

def get_mp3_tags(file):
    from mp3_tagger import MP3File
    if get_file_extension(file).lower() is not 'mp3':
        raise FileTypeError('File %s is not an mp3 file')
    # Create MP3File instance.
    mp3 = MP3File(file)
    return { 'artist' : mp3.artist, 'author' : mp3.artist, 'song' : mp3.song, 'title' : mp3.song, \
        'album' : mp3.album, 'year' : mp3.year, 'track' : mp3.track, 'genre' : mp3.genre, 'comment' : mp3.comment } 


