#!python3

import sys
import ffmpeg
import re
import os
import jprops
import json
import shutil
import videotools.filetools
from videotools.filetools import debug

class FileTypeError(Exception):
    pass

#PROPERTIES_FILE = r'E:\Tools\VideoTools.properties'
PROPERTIES_FILE = '/Users/Olivier/GitHub/audio-video-tools/VideoTools.properties'

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
    """Returns a dictionary of all parameters found on input string command line
    Parameters can be of the format -<option> <value> or -<option>"""
    found = True
    parms = dict()
    while (found):
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

def get_media_properties(props_file = None):
    """Returns all properties found in the properties file as dictionary"""
    if props_file is None:
        props_file = PROPERTIES_FILE
    try:
        properties = videotools.filetools.get_properties(props_file)
    except FileNotFoundError:
        properties['binaries.ffmpeg'] = 'ffmpeg'
        properties['binaries.ffprobe'] = 'ffprobe'
    return properties

def get_profile_extension(profile, properties = None):
    if properties is None:
        properties = get_media_properties()
    try:
        extension = properties[profile + '.extension']
    except KeyError:
        try:
            extension = properties['default.extension']
        except KeyError:
            extension = None
    return extension

def build_target_file(source_file, profile, properties):
    extension = get_profile_extension(profile, properties)
    if extension is None:
        extension = videotools.filetools.get_file_extension(source_file)
    return videotools.filetools.add_postfix(source_file, profile, extension)

def cmdline_options(**kwargs):
    # Returns ffmpeg cmd line options converted from clear options to ffmpeg format
    if kwargs is None:
        return {}
    
    mapping = { 'vframerate' : 'r', 'vbitrate':'b:v', 'abitrate' : 'b:a',
        'acodec' : 'acodec', 'vcodec' : 'vcodec', 'vsize' : 's', 'aspect' : 'aspect',
        'format': 'f'}
    params = {}
    for key in mapping.keys():
        try:
            params[mapping[key]] = kwargs[key]
        except KeyError:
            pass
    return params

def encode(source_file, target_file, profile, **kwargs):
    properties = get_media_properties(PROPERTIES_FILE)

    myprop = properties[profile + '.cmdline']
    if target_file is None:
        target_file = build_target_file(source_file, profile, properties)

    stream = ffmpeg.input(source_file)
    parms = get_params(myprop)
    parms.update(cmdline_options(**kwargs))

    #stream = ffmpeg.output(stream, target_file, acodec=getAudioCodec(myprop), ac=2, an=None, vcodec=getVideoCodec(myprop),  f=getFormat(myprop), aspect=getAspectRatio(myprop), s=getSize(myprop), r=getFrameRate(myprop)  )
    stream = ffmpeg.output(stream, target_file, **parms  )
    # -qscale:v 3  is **{'qscale:v': 3} 
    stream = ffmpeg.overwrite_output(stream)
    videotools.filetools.debug(2, ffmpeg.get_args(stream))
    videotools.filetools.debug(1, "%s --> %s" % (source_file, target_file))
    try:
        ffmpeg.run(stream, cmd=properties['binaries.ffmpeg'], capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        print(e.stderr, file=sys.stderr)
        sys.exit(1)

def encode_album_art(source_file, album_art_file, **kwargs):
    """Encodes album art image in an audio file after optionally resizing"""
    # profile = 'album_art' - # For the future, we'll use the cmd line associated to the profile in the config file
    properties = get_media_properties()
    target_file = videotools.filetools.add_postfix(source_file, 'album_art')

    if kwargs['scale'] is not None:
        w, h = re.split("x",kwargs['scale'])
        album_art_file = rescale(source_file, w, h)
        delete_aa_file = True

    # ffmpeg -i %1 -i %2 -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)" %1.mp3
    cmd = properties['binaries.ffmpeg'] + ' -i "' + source_file + '" -i "' + album_art_file \
        + '" -map 0:0 -map 1:0 -c copy -id3v2_version 3 ' \
        + ' -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)" ' \
        + '"' + target_file + '"'
    debug(1, "Running %s" % cmd)
    os.system(cmd)
    shutil.copy(target_file, source_file)
    os.remove(target_file)
    if delete_aa_file:
        os.remove(album_art_file)

def rescale(image_file, width, height, out_file = None):
    properties = get_media_properties()
    if out_file is None:
        out_file = videotools.filetools.add_postfix(image_file, "%dx%d" % (width,height))
    stream = ffmpeg.input(image_file)
    stream = ffmpeg.filter_(stream, 'scale', size= "%d:%d" % (width, height))
    stream = ffmpeg.output(stream, out_file)
    ffmpeg.run(stream, cmd=properties['binaries.ffmpeg'], capture_stdout=True, capture_stderr=True)
    return out_file

def probe_file(file):
    if videotools.filetools.is_media_file(file):
        try:
            properties = get_media_properties()
            return ffmpeg.probe(file, cmd=properties['binaries.ffprobe'])
        except AttributeError:
            print (dir(ffmpeg))
    else:
        raise FileTypeError('File %s is neither video, audio nor image file' % file)

def compute_fps(rate):
    if re.match(r"^\d+\/\d+$", rate):
        a, b = re.split(r'/', rate)
        return str(round(int(a)/int(b), 1))
    else:
        return rate

def reduce_aspect_ratio(w, h):
    for n in [2, 3, 5, 7, 11, 13, 17]:
        while w % n == 0 and h % n == 0:
            w = w // n
            h = h // n
    return "%d/%d" % (w, h)

def get_file_specs(file):
    probe_data = probe_file(file)
    debug(2, json.dumps(probe_data, sort_keys=True, indent=3, separators=(',', ': ')))
    myspecs = dict()
    myspecs['filename'] = probe_data['format']['filename']
    myspecs['filesize'] = probe_data['format']['size']
    #if file_type == 'image2':
    myspecs['type'] = videotools.filetools.get_file_type(file)
    if videotools.filetools.is_audio_file(file):
        myspecs['format'] = probe_data['streams'][0]['codec_name']
    #elif re.search(r'mp4', file_type) is not None:
    elif videotools.filetools.is_video_file(file):
        myspecs['format'] = videotools.filetools.get_file_extension(file)

    debug(1, "File type %s" % myspecs['type'])
    for stream in probe_data['streams']:
        try:
            if myspecs['type'] == 'image':
                myspecs['image_codec'] = stream['codec_name']
                myspecs['width'] = stream['width']
                myspecs['height'] = stream['height']
                myspecs['format'] = stream['codec_name']
            elif myspecs['type'] == 'video' and stream['codec_type'] == 'video':
                debug(2, "Getting stream data %s" % json.dumps(stream, sort_keys=True, indent=3, separators=(',', ': ')))
                myspecs['type'] = 'video'
                myspecs['video_codec'] = stream['codec_name']
                try:
                    myspecs['video_bitrate'] = stream['bit_rate']
                except KeyError:
                    pass
                myspecs['width'] = stream['width']
                myspecs['height'] = stream['height']
                myspecs['duration'] = stream['duration']
                myspecs['duration_hms'] = to_hms_str(stream['duration'])
                myspecs['video_fps'] = compute_fps(stream['r_frame_rate'])
                try:
                    myspecs['video_aspect_ratio'] = stream['display_aspect_ratio']
                except KeyError:
                    myspecs['video_aspect_ratio'] = reduce_aspect_ratio(myspecs['width'], myspecs['height'])
            elif (myspecs['type'] == 'audio' or myspecs['type'] == 'video') and stream['codec_type'] == 'audio':
                myspecs['audio_codec'] = stream['codec_name']
                myspecs['audio_sample_rate'] = stream['sample_rate']
                try:
                    myspecs['duration'] = stream['duration']
                    myspecs['duration_hms'] = to_hms_str(stream['duration'])
                except KeyError:
                    pass
                myspecs['audio_bitrate'] = stream['bit_rate']

        except KeyError as e:
            print("Stream %s has no key %s" % (str(stream), e.args[0]))
            print(myspecs)
            pass
    return myspecs

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
    if videotools.filetools.get_file_extension(file).lower() is not 'mp3':
        raise FileTypeError('File %s is not an mp3 file')
    # Create MP3File instance.
    mp3 = MP3File(file)
    return { 'artist' : mp3.artist, 'author' : mp3.artist, 'song' : mp3.song, 'title' : mp3.song, \
        'album' : mp3.album, 'year' : mp3.year, 'track' : mp3.track, 'genre' : mp3.genre, 'comment' : mp3.comment } 


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
    parser.add_argument('-i', '--inputfile', required=True,
                           help='Input File or Directory to encode'
                        )
    parser.add_argument('-o', '--outputfile', required=False,
                           help='Output file or directory'
                        )
    parser.add_argument('-p', '--profile', required=False,
                           help='Profile to use for encoding'
                        )
    parser.add_argument('-t', '--timeranges', required=False,
                           help='Time ranges to encode'
                        )
    parser.add_argument('-f', '--format', required=False,
                           help='Output file format'
                        )
    parser.add_argument('-r', '--framerate', required=False,
                           help='Framerate of the output'
                        )
    parser.add_argument('-g', '--debug', required=False,
                           help='Debug level'
                        )
    return parser

def cleanup_options(options):
    new_options = options.copy()
    for key in ['inputfile', 'outputfile', 'profile', 'debug']:
        del new_options[key]
    return new_options