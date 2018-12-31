#!python3

import sys
import platform
import re
import os
import json
import shutil
import jprops
import ffmpeg
import mediatools.utilities as util

class FileTypeError(Exception):
    '''Error when passing a non media file'''
    pass

class Encoder:
    '''Encoder abstraction'''
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
        '''Set Encoder properties according to ffmpeg conventions'''
        params = util.get_cmdline_params(props)
        for param in params.keys():
            if param is util.FFMPEG_FORMAT_OPTION:
                self.format = params[param]
            elif param is util.FFMPEG_VBITRATE_OPTION:
                self.vbitrate = params[param]
            elif param is util.FFMPEG_VCODEC_OPTION:
                self.vcodec = params[param]
            elif param is util.FFMPEG_ABITRATE_OPTION:
                self.abitrate = params[param]
            elif param is util.FFMPEG_ACODEC_OPTION:
                self.acodec = params[param]
            elif param is util.FFMPEG_DEINTERLACE_OPTION:
                self.deinterlace = ''
            elif param is util.FFMPEG_FPS_OPTION:
                self.fps = params[param]
            elif param is util.FFMPEG_SIZE_OPTION:
                self.size = params[param]
            elif param is util.FFMPEG_ASPECT_OPTION:
                self.aspect = params[param]
            elif param is util.FFMPEG_ACHANNELS_OPTION:
                self.achannels = params[param]
            elif param is util.FFMPEG_VFILTER_OPTION:
                self.vfilters.update({util.FFMPEG_VFILTER_OPTION:params[param]})

    def set_vcodec(self, vcodec):
        '''Set vcodec'''
        self.vcodec = vcodec

    def set_size(self, size):
        '''Set video size'''
        self.size = size

    def set_acodec(self, acodec):
        '''Set audio codec'''
        self.acodec = acodec

    def set_vbitrate(self, bitrate):
        '''Set video bitrate'''
        self.vbitrate = bitrate

    def set_abitrate(self, bitrate):
        '''Set audio bitrate'''
        self.abitrate = bitrate

    def set_deinterlace(self):
        '''Apply deinterlace'''
        self.deinterlace = ''

    def set_format(self, fmt):
        '''Set video file format'''
        self.format = fmt

    def build_ffmpeg_options(self):
        '''Builds string corresponding to ffmpeg conventions'''
        options = vars(self)
        cmd = ''
        for option in options.keys():
            if options[option] is not None:
                cmd = cmd + " -%s %s" % (util.OPTIONS_MAPPING[option], options[option])
        return cmd

class MediaFile:
    '''Media file abstraction'''
    def __init__(self, filename):
        if not util.is_media_file(filename):
            raise FileTypeError('File %s is neither video, audio nor image file' % filename)
        self.type = util.get_file_type(filename)
        self.filename = filename
        self.specs = None
        self.author = None
        self.year =  None
        self.copyright = None
        self.format = None
        self.format_long = None
        self.nb_streams = None
        self.size = None
        self.bitrate = None
        self.duration = None

    def get_filename(self):
        '''Returns file name'''
        return self.filename

    def get_author(self):
        '''Returns file author'''
        if self.author is None:
            self.get_specs()
        return self.author

    def get_filetype(self):
        '''Returns filetype'''
        return self.type

    def get_year(self):
        '''Returns file year'''
        if self.year is None:
            self.get_specs()
        return self.year

    def get_copyright(self):
        '''Returns file copyright'''
        if self.copyright is None:
            self.get_specs()
        return self.copyright

    def get_specs(self):
        '''Returns media file general specs'''
        if self.specs is None:
            self.specs = self.probe()
            util.debug(1, \
                json.dumps(self.specs, sort_keys=True, indent=3, separators=(',', ': ')))
        self.get_format_specs()
        return self.specs

    def get_format_specs(self):
        '''Reads file format specs'''
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
        '''Returns file properties as dict'''
        return {'filename':self.filename, 'type':self.type, 'format':self.format, \
        'nb_streams':self.nb_streams, 'filesize':self.size, 'duration': self.duration, \
        'bitrate':self.bitrate}

    def probe(self):
        ''' Returns file probe (media specs) '''
        try:
            properties = util.get_media_properties()
            return ffmpeg.probe(self.filename, cmd=properties['binaries.ffprobe'])
        except AttributeError:
            print (dir(ffmpeg))


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

def build_target_file(source_file, profile):
    extension = util.get_profile_extension(profile)
    if extension is None:
        extension = util.get_file_extension(source_file)
    return util.add_postfix(source_file, profile, extension)

def cmdline_options(**kwargs):
    # Returns ffmpeg cmd line options converted from clear options to ffmpeg format
    util.debug(2, 'Building cmd line options from %s' % str(kwargs))
    if kwargs is None:
        return {}
    params = {}
    for key in util.OPTIONS_MAPPING.keys():
        util.debug(5, "Checking option %s" % key)
        try:
            if kwargs[key] is not None:
                util.debug(5, "Found in cmd line with value %s" % kwargs[key])
                params[util.OPTIONS_MAPPING[key]] = kwargs[key]
        except KeyError:
            pass
    return params

def encode(source_file, target_file, profile, **kwargs):
    if target_file is None:
        target_file = build_target_file(source_file, profile)

    stream = ffmpeg.input(source_file)
    parms = util.get_profile_params(profile)
    parms.update(cmdline_options(**kwargs))

    # NOSONAR stream = ffmpeg.output(stream, target_file, acodec=getAudioCodec(myprop), ac=2, an=None,
    # vcodec=getVideoCodec(myprop),  f=getFormat(myprop), aspect=getAspectRatio(myprop),
    # s=getSize(myprop), r=getFrameRate(myprop)  )
    stream = ffmpeg.output(stream, target_file, **parms)
    # -qscale:v 3  is **{'qscale:v': 3}
    stream = ffmpeg.overwrite_output(stream)
    util.debug(2, ffmpeg.get_args(stream))
    util.debug(1, "%s --> %s" % (source_file, target_file))
    try:
        ffmpeg.run(stream, cmd=util.get_ffmpeg(), capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        print(e.stderr, file=sys.stderr)
        sys.exit(1)

def encode_album_art(source_file, album_art_file, **kwargs):
    """Encodes album art image in an audio file after optionally resizing"""
    # profile = 'album_art' - # For the future, we'll use the cmd line associated to the profile in the config file
    properties = util.get_media_properties()
    target_file = util.add_postfix(source_file, 'album_art')

    if kwargs['scale'] is not None:
        w, h = re.split("x", kwargs['scale'])
        album_art_file = rescale(source_file, w, h)
        delete_aa_file = True

    # ffmpeg -i %1 -i %2 -map 0:0 -map 1:0 -c copy -id3v2_version 3
    # -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)" %1.mp3
    cmd = properties['binaries.ffmpeg'] + ' -i "' + source_file + '" -i "' + album_art_file \
        + '" -map 0:0 -map 1:0 -c copy -id3v2_version 3 ' \
        + ' -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)" ' \
        + '"' + target_file + '"'
    util.debug(1, "Running %s" % cmd)
    os.system(cmd)
    shutil.copy(target_file, source_file)
    os.remove(target_file)
    if delete_aa_file:
        os.remove(album_art_file)

def rescale(image_file, width, height, out_file=None):
    properties = util.get_media_properties()
    if out_file is None:
        out_file = util.add_postfix(image_file, "%dx%d" % (width, height))
    stream = ffmpeg.input(image_file)
    stream = ffmpeg.filter_(stream, 'scale', size= "%d:%d" % (width, height))
    stream = ffmpeg.output(stream, out_file)
    ffmpeg.run(stream, cmd=properties['binaries.ffmpeg'], capture_stdout=True, capture_stderr=True)
    return out_file

def get_crop_filter_options(width, height, top, left):
    # ffmpeg -i in.mp4 -filter:v "crop=out_w:out_h:x:y" out.mp4
    return "-filter:v crop=%d:%d:%d:%d" % (width, height, top, left)

def get_deshake_filter_options(width, height):
    # ffmpeg -i <in> -f mp4 -vf deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=16 -b:v 2048k <out>
    return "-vf deshake=x=-1:y=-1:w=-1:h=-1:rx=%d:ry=%d" % (width, height)

def deshake(video_file, width, height, out_file=None):
    ''' Applies deshake video filter for width x height pixels '''
    properties = util.get_media_properties()
    if out_file is None:
        out_file = util.add_postfix(video_file, "deshake_%dx%d" % (width, height))
    cmd = "%s -i %s %s -vcodec libx264 -deinterlace %s" % \
        (properties['binaries.ffmpeg'], video_file, get_deshake_filter_options(width, height), out_file)
    util.debug(1, "Running %s" % cmd)
    os.system(cmd)
    return out_file

def crop(video_file, width, height, top, left, out_file = None):
    ''' Applies crop video filter for width x height pixels '''
    properties = util.get_media_properties()
    if out_file is None:
        out_file = util.add_postfix(video_file, "crop_%dx%d-%dx%d" % (width, height, top, left))
    aw, ah = re.split("/", reduce_aspect_ratio(width, height))
    cmd = "%s -i %s %s -vcodec libx264 -aspect %d:%d %s" % \
        (properties['binaries.ffmpeg'], video_file, get_crop_filter_options(width, height, top, left), \
        int(aw), int(ah), out_file)
    util.debug(2, "Running %s" % cmd)
    os.system(cmd)
    return out_file

def probe_file(file):
    ''' Returns file probe (media specs) '''
    if util.is_media_file(file):
        try:
            properties = util.get_media_properties()
            return ffmpeg.probe(file, cmd=properties['binaries.ffprobe'])
        except AttributeError:
            print(dir(ffmpeg))
    else:
        raise FileTypeError('File %s is neither video, audio nor image file' % file)

def compute_fps(rate):
    ''' Simplifies the FPS calculation '''
    if re.match(r"^\d+\/\d+$", rate):
        a, b = re.split(r'/', rate)
        return str(round(int(a)/int(b), 1))
    else:
        return rate

def reduce_aspect_ratio(aspect_ratio, height=None):
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
    util.debug(2, "Getting stream data %s" % json.dumps(stream, sort_keys=True, indent=3, separators=(',', ': ')))
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
    util.debug(2, json.dumps(probe_data, sort_keys=True, indent=3, separators=(',', ': ')))
    specs = {}
    specs['filename'] = probe_data['format']['filename']
    specs['filesize'] = probe_data['format']['size']
    #if file_type == 'image2':
    specs['type'] = util.get_file_type(file)
    if util.is_audio_file(file):
        specs['format'] = probe_data['streams'][0]['codec_name']
    #elif re.search(r'mp4', file_type) is not None:
    elif util.is_video_file(file):
        specs['format'] = util.get_file_extension(file)

    util.debug(1, "File type %s" % specs['type'])
    for stream in probe_data['streams']:
        try:
            if specs['type'] == 'image':
                specs.update(get_image_specs(stream))
            elif specs['type'] == 'video' and stream['codec_type'] == 'video':
                specs.update(get_video_specs(stream))
            elif (specs['type'] == 'audio' or specs['type'] == 'video') and stream['codec_type'] == 'audio':
                specs.update(get_audio_specs(stream))
        except KeyError as e:
            util.debug(1, "Stream %s has no key %s" % (str(stream), e.args[0]))
            util.debug(1, str(specs))
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
    if util.get_file_extension(file).lower() is not 'mp3':
        raise FileTypeError('File %s is not an mp3 file')
    # Create MP3File instance.
    mp3 = MP3File(file)
    return {'artist' : mp3.artist, 'author' : mp3.artist, 'song' : mp3.song, 'title' : mp3.song, \
        'album' : mp3.album, 'year' : mp3.year, 'track' : mp3.track, 'genre' : mp3.genre, 'comment' : mp3.comment}


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
    parser.add_argument('-g', '--util.debug', required=False, help='util.debug level')
    return parser

def cleanup_options(options):
    new_options = options.copy()
    for key in ['inputfile', 'outputfile', 'profile', 'util.debug']:
        del new_options[key]
    return new_options

def concat(target_file, file_list):
#    ffmpeg -i opening.mkv -i episode.mkv -i ending.mkv \
#  -filter_complex "[0:v] [0:a] [1:v] [1:a] [2:v] [2:a] concat=n=3:v=1:a=1 [v] [a]" \
#  -map "[v]" -map "[a]" output.mkv
    properties = util.get_media_properties()
    cmd = properties['binaries.ffmpeg']
    util.debug(2, str(file_list))
    for file in file_list:
        cmd = cmd + (' -i "%s" ' % file)
    count = 0
    cmd = cmd + '-filter_complex "'
    for file in file_list:
        cmd = cmd + ("[%d:v] [%d:a]" % (count, count))
        count = count + 1
    cmd = cmd + 'concat=n=%d:v=1:a=1 [v] [a]" -map "[v]" -map "[a]" %s' % (count, target_file)
    util.debug(1, "Running %s" % cmd)
    os.system(cmd)

def build_ffmpeg_options(options):
    cmd = ''
    for option in options.keys():
        if options[option] is not None:
            cmd = cmd + " -%s %s" % (option, options[option])
    return cmd
