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
import platform

FFMPEG_FORMAT_OPTION = 'f'
FFMPEG_SIZE_OPTION = 's'
FFMPEG_VCODEC_OPTION = 'vcodec'
FFMPEG_ACODEC_OPTION = 'acodec'
FFMPEG_VBITRATE_OPTION = 'b:v'
FFMPEG_ABITRATE_OPTION = 'a:v'
FFMPEG_SIZE_OPTION = 's'
FFMPEG_FPS_OPTION = 'r'
FFMPEG_ASPECT_OPTION = 'aspect'
FFMPEG_DEINTERLACE_OPTION = 'deinterlace'
FFMPEG_ACHANNELS_OPTION = 'ac'
FFMPEG_VFILTER_OPTION = 'vf'

OPTIONS_MAPPING = { 'format':FFMPEG_FORMAT_OPTION, \
   'vcodec':FFMPEG_VCODEC_OPTION, 'vbitrate':FFMPEG_VBITRATE_OPTION, \
   'acodec':FFMPEG_ACODEC_OPTION, 'abitrate':FFMPEG_ABITRATE_OPTION, \
   'fps':FFMPEG_FPS_OPTION, 'aspect':FFMPEG_ASPECT_OPTION, 'size':FFMPEG_SIZE_OPTION, \
   'deinterlace':FFMPEG_DEINTERLACE_OPTION, 'achannels':FFMPEG_ACHANNELS_OPTION, \
   'vfilter':FFMPEG_VFILTER_OPTION }

class FileTypeError(Exception):
    pass

if platform.system() is 'Windows':
    PROPERTIES_FILE = r'E:\Tools\VideoTools.properties'
else:
    PROPERTIES_FILE = '/Users/Olivier/GitHub/audio-video-tools/VideoTools.properties'

class Encoder:
    def __init__(self):
        self.format = None
        self.vcodec = None # 'libx264'
        self.acodec = None # 'libvo_aacenc'
        self.vbitrate = None # '2048k'
        self.abitrate = None # '128k'
        self.fps = None
        self.aspect = None
        self.size = None
        self.deinterlace = None
        self.achannels = None
        self.vfilters = {}
        self.other_options = {}

    def set_ffmpeg_properties(self, props):
        params = get_params(props)
        for param in params.keys():
            # internal_keys = OPTIONS_MAPPING.keys()
            if param is FFMPEG_FORMAT_OPTION:
                self.format = params[param]
            elif param is FFMPEG_VBITRATE_OPTION:
                self.vbitrate = params[param]
            elif param is FFMPEG_VCODEC_OPTION:
                self.vcodec = params[param]
            elif param is FFMPEG_ABITRATE_OPTION:
                self.abitrate = params[param]
            elif param is FFMPEG_ACODEC_OPTION:
                self.acodec = params[param]
            elif param is FFMPEG_DEINTERLACE_OPTION:
                self.deinterlace = ''
            elif param is FFMPEG_FPS_OPTION:
                self.fps = params[param]
            elif param is FFMPEG_SIZE_OPTION:
                self.size = params[param]
            elif param is FFMPEG_ASPECT_OPTION:
                self.aspect = params[param]
            elif param is FFMPEG_ACHANNELS_OPTION:
                self.achannels = params[param]
            elif param is FFMPEG_VFILTER_OPTION:
                self.vfilters.update({FFMPEG_VFILTER_OPTION:params[param]})

    def set_vcodec(self, vcodec):
        self.vcodec = vcodec

    def set_size(self, size):
        self.size = size

    def set_acodec(self, acodec):
        self.acodec = acodec
    
    def set_vbitrate(self, bitrate):
        self.vbitrate = bitrate

    def set_abitrate(self, bitrate):
        self.abitrate = bitrate

    def set_deinterlace(self):
        self.deinterlace = ''
        
    def set_format(self, fmt):
        self.format = fmt
    
    def build_ffmpeg_options(self):
        options = vars(self)
        cmd = ''
        for option in options.keys():
            if options[option] is not None:
                cmd = cmd + " -%s %s" % (OPTIONS_MAPPING[option], options[option])
        return cmd

class MediaFile:
    def __init__(self, filename):
        if not videotools.filetools.is_media_file(filename):
            raise FileTypeError('File %s is neither video, audio nor image file' % filename)
        self.type = videotools.filetools.get_file_type(filename)
        self.filename = filename
        self.specs = None
        self.author = None
        self.year =  None
        self.copyright = None
        self.format = None
    
    def get_filename(self):
        return self.filename

    def get_author(self):
        if self.author is None:
            self.get_specs()
        return self.author

    def get_filetype(self):
        return self.type

    def get_year(self):
        if self.year is None:
            self.get_specs()
        return self.year

    def get_copyright(self):
        if self.copyright is None:
            self.get_specs()
        return self.copyright

    def get_specs(self):
        if self.specs is None:
            self.specs = self.probe()
            videotools.filetools.debug(1, \
                json.dumps(self.specs, sort_keys=True, indent=3, separators=(',', ': ')))
        self.get_format_specs()
        return self.specs

    def get_format_specs(self):
        self.format = self.specs['format']['format_name']
        self.format_long = self.specs['format']['format_long_name']
        self.nb_streams = self.specs['format']['nb_streams']
        self.size = self.specs['format']['size']
        try:
            self.bitrate = self.specs['format']['bit_rate']
        except KeyError:
            pass
        try:
            self.duration = self.specs['format']['duration']
        except KeyError:
            pass

    def get_file_properties(self):
        return {'filename':self.filename, 'type':self.type, 'format':self.format, 'nb_streams':self.nb_streams, 'filesize':self.size, 'duration': self.duration, 'bitrate':self.bitrate}

    def probe(self):
        ''' Returns file probe (media specs) '''
        try:
            properties = get_media_properties()
            return ffmpeg.probe(self.filename, cmd=properties['binaries.ffprobe'])
        except AttributeError:
            print (dir(ffmpeg))

class AudioFile(MediaFile):
    def __init__(self, filename):
        super(AudioFile, self).__init__(filename)
        self.audio_codec = None
        self.artist = None
        self.title = None
        self.author = None
        self.album = None
        self.year = None
        self.track = None
        self.genre = None
        self.comment = None

    def get_audio_specs(self):
        for stream in self.specs['streams']:
            if stream['codec_type'] == 'audio':
                try:
                    self.audio_bitrate = stream['bit_rate']
                    self.duration = stream['duration']
                    self.audio_codec = stream['codec_name']
                    self.audio_sample_rate = stream['sample_rate']
                except KeyError as e:
                    debug(1, "Stream %s has no key %s\n%s" % (str(stream), e.args[0], str(stream)))
        return self.specs

    def get_tags(self):
        from mp3_tagger import MP3File
        if videotools.filetools.get_file_extension(self.filename).lower() is not 'mp3':
            raise FileTypeError('File %s is not an mp3 file')
            # Create MP3File instance.
        mp3 = MP3File(self.filename)
        self.artist = mp3.artist
        self.title = mp3.song
        self.album = mp3.album
        self.year = mp3.year
        self.track = mp3.track
        self.genre = mp3.genre
        self.comment = mp3.comment

    def get_title(self):
        if self.title is None:
            self.get_tags()
        return self.title

    def get_album(self):
        if self.album is None:
            self.get_tags()
        return self.album

    def get_author(self):
        if self.author is None:
            self.get_tags()
        return self.author
    
    def get_track(self):
        if self.track is None:
            self.get_tags()
        return self.track
    
    def get_year(self):
        if self.year is None:
            self.get_tags()
        return self.year

    def get_genre(self):
        if self.genre is None:
            self.get_tags()
        return self.genre
    
    def get_properties(self):
        if self.audio_codec is None:
            self.get_specs()
        all_specs = self.get_file_properties()
        all_specs.update({'file_size':self.size, 'file_format':self.format, 'audio_bitrate': self.audio_bitrate, 'audio_codec': self.audio_codec, 'audio_sample_rate':self.audio_sample_rate, 'author': self.author, 'year': self.year, 'title':self.title, 'track':self.track, 'genre':self.genre, 'album':self.album })
        return  all_specs

    def get_specs(self):
        super(AudioFile, self).get_specs()
        self.get_audio_specs()

class VideoFile(MediaFile):
    def __init__(self, filename):
        super(VideoFile, self).__init__(filename)
        self.aspect = None
        self.get_specs()
    
    def get_specs(self):
        super(VideoFile, self).get_specs()
        self.get_video_specs()
        self.get_audio_specs()
        
    def get_video_specs(self):  
        for stream in self.specs['streams']:
            if stream['codec_type'] == 'video':
                try:
                    self.video_codec = stream['codec_name']
                    self.video_bitrate = get_video_bitrate(stream)
                    self.width = int(stream['width'])
                    self.height = int(stream['height'])
                    self.duration = stream['duration']
                    self.video_fps = compute_fps(stream['avg_frame_rate'])
                except KeyError as e:
                    debug(1, "Stream %s has no key %s\n%s" % (str(stream), e.args[0], str(stream)))
                try:
                    ar = stream['display_aspect_ratio']
                except KeyError:
                    ar = reduce_aspect_ratio("%d:%d" % (self.width, self.height))
                self.aspect = reduce_aspect_ratio(ar)
                try:
                    par = stream['sample_aspect_ratio']
                except KeyError:
                    par = reduce_aspect_ratio("%d:%d" % (self.width, self.height))
                self.pixel_aspect = reduce_aspect_ratio(par)
        return self.specs

    def get_audio_specs(self):
        for stream in self.specs['streams']:
            if stream['codec_type'] == 'audio':
                try:
                    self.audio_codec = stream['codec_name']
                    self.audio_bitrate = stream['bit_rate']
                    self.audio_sample_rate = stream['sample_rate']
                except KeyError as e:
                    debug(1, "Stream %s has no key %s\n%s" % (str(stream), e.args[0], str(stream)))
        return self.specs

    def get_aspect_ratio(self):
        if self.aspect is None:
            self.get_specs()
        return self.aspect

    def get_pixel_aspect_ratio(self):
        if self.pixel_aspect is None:
            self.get_specs()
        return self.pixel_aspect

    def get_video_codec(self):
        if self.video_codec is None:
            self.get_specs()
        return self.video_codec

    def get_video_bitrate(self):
        if self.video_bitrate is None:
            self.get_specs()
        return self.video_bitrate

    def get_audio_codec(self):
        if self.audio_codec is None:
            self.get_specs()
        return self.audio_codec

    def get_audio_bitrate(self):
        if self.audio_bitrate is None:
            self.get_specs()
        return self.audio_bitrate

    def get_fps(self):
        if self.video_fps is None:
            self.get_specs()
        return self.video_fps

    def get_duration(self):
        if self.duration is None:
            self.get_specs()
        return self.duration

    def get_height(self):
        if self.height is None:
            self.get_specs()
        return self.height

    def get_width(self):
        if self.width is None:
            self.get_specs()
        return self.width

    def get_dimensions(self):
        if self.width is None or self.height is None:
            self.get_specs()
        return self.width, self.height

    def get_audio_properties(self):
        if self.audio_codec is None:
            self.get_specs()
        return {'audio_bitrate': self.audio_bitrate, 'audio_codec': self.audio_codec, 'audio_sample_rate':self.audio_sample_rate }

    def get_video_properties(self):
        if self.video_codec is None:
            self.get_specs()
        return {'file_size':self.size, 'file_format': self.format, 'video_bitrate': self.video_bitrate, 'video_codec': self.video_codec, 'video_fps':self.video_fps, 'width':self.width, 'height': self.height, 'aspect_ratio': self.aspect,'pixel_aspect_ratio': self.pixel_aspect,'author': self.author, 'copyright': self.copyright, 'year':self.year }

    def get_properties(self):
        all_props = self.get_file_properties()
        all_props.update(self.get_audio_properties())
        all_props.update(self.get_video_properties())
        return all_props

    def get_ffmpeg_params(self):
        mapping = { 'audio_bitrate':'b:a', 'audio_codec':'acodec', 'video_bitrate':'b:v', 'video_codec':'vcodec'}
        props = self.get_properties()
        ffmpeg_parms = {}
        for key in mapping.keys():
            if props[key] is not None and props[key] is not '':
                ffmpeg_parms[mapping[key]] = props[key]
        return ffmpeg_parms

    def encode(self, target_file, profile):
        # stream = ffmpeg.input(self.filename)
        self.stream = ffmpeg.output(self.stream, target_file, acodec='libvo_aacenc', vcodec='libx264', f='mp4', vr='2048k', ar='128k' )
        self.stream = ffmpeg.overwrite_output(self.stream)

        try:
            ffmpeg.run(self.stream)
        except ffmpeg.Error as e:
            print(e.stderr, file=sys.stderr)
            sys.exit(1)
    
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

def get_video_bitrate_option(cmdline):
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
    global OPTIONS_MAPPING
    debug(2, 'Building cmd line options from %s' % str(kwargs))
    if kwargs is None:
        return {}  
    params = {}
    for key in OPTIONS_MAPPING.keys():
        debug(5, "Checking option %s" % key)
        try:
            if kwargs[key] is not None:
                debug(5, "Found in cmd line with value %s" % kwargs[key])
                params[OPTIONS_MAPPING[key]] = kwargs[key]
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

def encodeoo(source_file, target_file, profile, **kwargs):
    properties = get_media_properties(PROPERTIES_FILE)

    profile_options = properties[profile + '.cmdline']
    if target_file is None:
        target_file = build_target_file(source_file, profile, properties)


    file_o = VideoFile(source_file)
    parms = file_o.get_ffmpeg_params()
    debug(1, "File settings = %s" % str(parms))
    parms.update(get_params(profile_options))
    debug(1, "Profile settings = %s" % str(parms))
    parms.update(cmdline_options(**kwargs))
    debug(1, "Cmd line settings = %s" % str(parms))

    cmd = "%s -i %s %s %s" % (properties['binaries.ffmpeg'], source_file, build_ffmpeg_options(parms), target_file)
    debug(1, "Running %s" % cmd)
    os.system(cmd)

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

def get_deshake_filter_options(width, height):
    # ffmpeg -i <in> -f mp4 -vf deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=16 -b:v 2048k <out>
    return "-vf deshake=x=-1:y=-1:w=-1:h=-1:rx=%d:ry=%d" % (width, height)

def deshake(video_file, width, height, out_file = None):
    ''' Applies deshake video filter for width x height pixels '''
    properties = get_media_properties()
    if out_file is None:
        out_file = videotools.filetools.add_postfix(video_file, "deshake_%dx%d" % (width,height))
    cmd = "%s -i %s %s %s" % \
        (properties['binaries.ffmpeg'], video_file, get_deshake_filter_options(width, height), out_file)
    debug(1, "Running %s" % cmd)
    os.system(cmd)
    return out_file

def probe_file(file):
    ''' Returns file probe (media specs) '''
    if videotools.filetools.is_media_file(file):
        try:
            properties = get_media_properties()
            return ffmpeg.probe(file, cmd=properties['binaries.ffprobe'])
        except AttributeError:
            print (dir(ffmpeg))
    else:
        raise FileTypeError('File %s is neither video, audio nor image file' % file)

def compute_fps(rate):
    ''' Simplifies the FPS calculation '''
    if re.match(r"^\d+\/\d+$", rate):
        a, b = re.split(r'/', rate)
        return str(round(int(a)/int(b), 1))
    else:
        return rate

def reduce_aspect_ratio(aspect_ratio, height = None):
    ''' Reduces the Aspect ratio calculation in prime factors '''
    if height is None:
        ws, hs = re.split("[:/x]", aspect_ratio)
        w = int(ws)
        h = int(hs)
    else:
        w = aspect_ratio
        h = height
    for n in [2, 3, 5, 7, 11, 13, 17]:
        while w % n == 0 and h % n == 0:
            w = w // n
            h = h // n
    return "%d:%d" % (w, h)

def get_audio_specs(stream):
    specs = {}
    specs['audio_codec'] = stream['codec_name']
    specs['audio_sample_rate'] = stream['sample_rate']
    try:
        specs['duration'] = stream['duration']
        specs['duration_hms'] = to_hms_str(stream['duration'])
    except KeyError:
        pass
    specs['audio_bitrate'] = stream['bit_rate']
    return specs

def get_video_bitrate(stream):
    bitrate = None
    try:
        bitrate = stream['bit_rate']
    except KeyError:
        try:
            bitrate = stream['duration_ts']
        except KeyError:
            pass
    return bitrate

def get_video_specs(stream):
    debug(2, "Getting stream data %s" % json.dumps(stream, sort_keys=True, indent=3, separators=(',', ': ')))
    specs = {}
    specs['type'] = 'video'
    specs['video_codec'] = stream['codec_name']
    specs['video_bitrate'] = get_video_bitrate(stream)
    specs['width'] = stream['width']
    specs['height'] = stream['height']
    specs['duration'] = stream['duration']
    specs['duration_hms'] = to_hms_str(stream['duration'])
    raw_fps = stream['avg_frame_rate'] if 'avg_frame_rate' in stream.keys() else stream['r_frame_rate']
    specs['video_fps'] = compute_fps(raw_fps)
    try:
        specs['video_aspect_ratio'] = stream['display_aspect_ratio']
    except KeyError:
        specs['video_aspect_ratio'] = reduce_aspect_ratio(specs['width'], specs['height'])
    return specs

def get_image_specs(stream):
    specs = {}
    specs['image_codec'] = stream['codec_name']
    specs['width'] = stream['width']
    specs['height'] = stream['height']
    specs['format'] = stream['codec_name']
    return specs

def get_file_specs(file):
    probe_data = probe_file(file)
    debug(2, json.dumps(probe_data, sort_keys=True, indent=3, separators=(',', ': ')))
    specs = {}
    specs['filename'] = probe_data['format']['filename']
    specs['filesize'] = probe_data['format']['size']
    #if file_type == 'image2':
    specs['type'] = videotools.filetools.get_file_type(file)
    if videotools.filetools.is_audio_file(file):
        specs['format'] = probe_data['streams'][0]['codec_name']
    #elif re.search(r'mp4', file_type) is not None:
    elif videotools.filetools.is_video_file(file):
        specs['format'] = videotools.filetools.get_file_extension(file)

    debug(1, "File type %s" % specs['type'])
    for stream in probe_data['streams']:
        try:
            if specs['type'] == 'image':
                specs.update(get_image_specs(stream))
            elif specs['type'] == 'video' and stream['codec_type'] == 'video':
                specs.update(get_video_specs(stream))
            elif (specs['type'] == 'audio' or specs['type'] == 'video') and stream['codec_type'] == 'audio':
                specs.update(get_audio_specs(stream))
        except KeyError as e:
            debug(1, "Stream %s has no key %s" % (str(stream), e.args[0]))
            debug(1, str(specs))
    return specs

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
    parser.add_argument('-i', '--inputfile', required=True, help='Input File or Directory to encode')
    parser.add_argument('-o', '--outputfile', required=False, help='Output file or directory')
    parser.add_argument('-p', '--profile', required=False, help='Profile to use for encoding')
    parser.add_argument('-t', '--timeranges', required=False, help='Time ranges to encode')
    parser.add_argument('-f', '--format', required=False, help='Output file format')
    parser.add_argument('-r', '--fps', required=False, help='Video framerate of the output')
    parser.add_argument('--acodec', required=False, help='Audio codec (mp3, aac, ac3...)')
    parser.add_argument('--abitrate', required=False, help='Audio bitrate')
    parser.add_argument('--asampling', required=False, help='Audio sampling')
    parser.add_argument('--vcodec', required=False, help='Video codec (h264, h265, mp4, mpeg2, xvid...)')
    parser.add_argument('--vsize', required=False, help='Video size HxW')
    parser.add_argument('--vbitrate', required=False, help='Video bitrate')
    parser.add_argument('--aspect', required=False, help='Aspect Ratio 16:9, 4:3, 1.5 ...')
    parser.add_argument('--ranges', required=False, help='Ranges of encoding <start>:<end>,<start>:<end>')
    parser.add_argument('-g', '--debug', required=False, help='Debug level')
    return parser

def cleanup_options(options):
    new_options = options.copy()
    for key in ['inputfile', 'outputfile', 'profile', 'debug']:
        del new_options[key]
    return new_options

def concat(target_file, filelist):
#    ffmpeg -i opening.mkv -i episode.mkv -i ending.mkv \
#  -filter_complex "[0:v] [0:a] [1:v] [1:a] [2:v] [2:a] concat=n=3:v=1:a=1 [v] [a]" \
#  -map "[v]" -map "[a]" output.mkv
    properties = get_media_properties()
    cmd = properties['binaries.ffmpeg']
    debug(2, str(filelist))
    for file in filelist:
        cmd = cmd + (' -i "%s" ' % file)
    count = 0
    cmd = cmd + '-filter_complex "'
    for file in filelist:
        cmd = cmd + ("[%d:v] [%d:a]" % (count, count))
        count = count + 1
    cmd = cmd + 'concat=n=%d:v=1:a=1 [v] [a]" -map "[v]" -map "[a]" %s' % (count, target_file)
    debug(1, "Running %s" % cmd)
    os.system(cmd)

def build_ffmpeg_options(options):
    cmd = ''
    for option in options.keys():
        if options[option] is not None:
            cmd = cmd + " -%s %s" % (option, options[option])
    return cmd