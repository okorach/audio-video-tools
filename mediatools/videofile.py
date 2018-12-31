#!python3
'''Video file tools'''

import sys
import re
import os
import json
import shutil
import ffmpeg
import jprops
import mediatools.utilities as util
from mediatools.mediafile import MediaFile, FileTypeError

class VideoFile(MediaFile):
    '''Video file abstraction'''
    def __init__(self, filename):
        super(VideoFile, self).__init__(filename)
        self.aspect = None
        self.video_codec = None
        self.video_bitrate = None
        self.width = None
        self.height = None
        self.duration = None
        self.video_fps = None
        self.pixel_aspect = None
        self.audio_bitrate = None
        self.audio_codec = None
        self.audio_sample_rate = None
        self.stream = None
        self.get_specs()

    def get_specs(self):
        '''Returns video file complete specs as dict'''
        super(VideoFile, self).get_specs()
        self.get_video_specs()
        self.get_audio_specs()

    def get_video_specs(self):
        '''Returns video file video specs as dict'''
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
                    util.debug(1, "Stream %s has no key %s\n%s" % (str(stream), e.args[0], str(stream)))
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
        '''Returns video file audio specs as dict'''
        for stream in self.specs['streams']:
            if stream['codec_type'] == 'audio':
                try:
                    self.audio_codec = stream['codec_name']
                    self.audio_bitrate = stream['bit_rate']
                    self.audio_sample_rate = stream['sample_rate']
                except KeyError as e:
                    util.debug(1, "Stream %s has no key %s\n%s" % (str(stream), e.args[0], str(stream)))
        return self.specs

    def get_aspect_ratio(self):
        '''Returns video file aspect ratio'''
        if self.aspect is None:
            self.get_specs()
        return self.aspect

    def get_pixel_aspect_ratio(self):
        '''Returns video file pixel aspect ratio'''
        if self.pixel_aspect is None:
            self.get_specs()
        return self.pixel_aspect

    def get_video_codec(self):
        '''Returns video file video codec'''
        if self.video_codec is None:
            self.get_specs()
        return self.video_codec

    def get_video_bitrate(self):
        '''Returns video file video bitrate'''
        if self.video_bitrate is None:
            self.get_specs()
        return self.video_bitrate

    def get_audio_codec(self):
        '''Returns video file audio codec'''
        if self.audio_codec is None:
            self.get_specs()
        return self.audio_codec

    def get_audio_bitrate(self):
        '''Returns video file audio bitrate'''
        if self.audio_bitrate is None:
            self.get_specs()
        return self.audio_bitrate

    def get_fps(self):
        if self.video_fps is None:
            self.get_specs()
        return self.video_fps

    def get_duration(self):
        '''Returns video file duration'''
        if self.duration is None:
            self.get_specs()
        return self.duration

    def get_height(self):
        '''Returns video file height'''
        if self.height is None:
            self.get_specs()
        return self.height

    def get_width(self):
        '''Returns video file width'''
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
        return {'audio_bitrate': self.audio_bitrate, 'audio_codec': self.audio_codec, \
        'audio_sample_rate':self.audio_sample_rate }

    def get_video_properties(self):
        if self.video_codec is None:
            self.get_specs()
        return {'file_size':self.size, 'file_format': self.format, 'video_bitrate': self.video_bitrate, \
        'video_codec': self.video_codec, 'video_fps':self.video_fps, \
        'width':self.width, 'height': self.height, 'aspect_ratio': self.aspect, \
        'pixel_aspect_ratio': self.pixel_aspect,'author': self.author, \
        'copyright': self.copyright, 'year':self.year }

    def get_properties(self):
        all_props = self.get_file_properties()
        all_props.update(self.get_audio_properties())
        all_props.update(self.get_video_properties())
        return all_props

    def build_encoding_options(self, **kwargs):
        parms = self.get_ffmpeg_params()
        util.debug(1, "File settings = %s" % str(parms))
        if 'profile' in kwargs.keys():
            parms.update(util.get_cmdline_params(kwargs['profile']))
        util.debug(1, "Profile settings = %s" % str(parms))
        clean_options = util.cleanup_options(**kwargs)
        parms.update(cmdline_options(**clean_options))
        util.debug(1, "Cmd line settings = %s" % str(parms))

    def get_ffmpeg_params(self):
        mapping = { 'audio_bitrate':'b:a', 'audio_codec':'acodec', 'video_bitrate':'b:v', 'video_codec':'vcodec'}
        props = self.get_properties()
        ffmpeg_parms = {}
        for key in mapping.keys():
            if props[key] is not None and props[key] is not '':
                ffmpeg_parms[mapping[key]] = props[key]
        return ffmpeg_parms

    def encode(self, target_file, profile):
        self.stream = ffmpeg.input(self.filename)
        self.stream = ffmpeg.output(self.stream, target_file, acodec='libvo_aacenc', vcodec='libx264', \
            f='mp4', vr='2048k', ar='128k' )
        self.stream = ffmpeg.overwrite_output(self.stream)

        try:
            ffmpeg.run(self.stream)
        except ffmpeg.Error as e:
            print(e.stderr, file=sys.stderr)
            sys.exit(1)

    def scale(self, scale):
        self.stream = ffmpeg.filter_(self.stream, 'scale', size=scale)

    def crop(self, width, height, top, left, out_file, **kwargs):
        ''' Applies crop video filter for width x height pixels '''
        parms = self.get_ffmpeg_params()
        clean_options = util.cleanup_options(kwargs)
        parms.update(cmdline_options(**clean_options))
        util.debug(1, "Cmd line settings = %s" % str(parms))
        if out_file is None:
            out_file = util.add_postfix(self.filename, "crop_%dx%d-%dx%d" % (width, height, top, left))
        aw, ah = re.split(":", reduce_aspect_ratio(width, height))
        cmd = "%s -i %s %s %s -aspect %d:%d %s" % (util.get_ffmpeg(), self.filename, \
            build_ffmpeg_options(parms), get_crop_filter_options(width, height, top, left), \
            int(aw), int(ah), out_file)
        util.debug(1, "Running %s" % cmd)
        os.system(cmd)
        return out_file

    def get_metadata(self):
        return ffmpeg.probe(self.filename)

    def set_author(self, author):
        self.author = author

    def get_author(self):
        return self.author

    def set_copyright(self, copyr):
        self.copyright = copyr

    def get_copyright(self):
        return self.copyright

def get_size_option(cmdline):
    m = re.search(r'-s\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_video_codec_option(cmdline):
    m = re.search(r'-vcodec\s+(\S+)', cmdline)
    if m:
        return m.group(1)
    m = re.search(r'-c:v\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_audio_codec_option(cmdline):
    m = re.search(r'-acodec\s+(\S+)', cmdline)
    if m:
        return m.group(1)
    m = re.search(r'-c:a\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_format_option(cmdline):
    m = re.search(r'-f\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_audio_bitrate_option(cmdline):
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

def get_aspect_ratio_option(cmdline):
    m = re.search(r'-aspect\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def get_frame_rate_option(cmdline):
    m = re.search(r'-r\s+(\S+)', cmdline)
    return m.group(1) if m else ''

def build_target_file(source_file, profile, properties):
    extension = util.get_profile_extension(profile, properties)
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
    properties = util.get_media_properties()
    if target_file is None:
        target_file = build_target_file(source_file, profile, properties)

    stream = ffmpeg.input(source_file)
    parms = util.get_profile_params(profile)
    parms.update(cmdline_options(**kwargs))

    # NOSONAR stream = ffmpeg.output(stream, target_file, acodec=getAudioCodec(myprop), ac=2, an=None,
    # vcodec=getVideoCodec(myprop),  f=getFormat(myprop), aspect=getAspectRatio(myprop),
    # s=getSize(myprop), r=getFrameRate(myprop)  )
    stream = ffmpeg.output(stream, target_file, **parms  )
    # -qscale:v 3  is **{'qscale:v': 3}
    stream = ffmpeg.overwrite_output(stream)
    util.debug(2, ffmpeg.get_args(stream))
    util.debug(1, "%s --> %s" % (source_file, target_file))
    try:
        ffmpeg.run(stream, cmd=properties['binaries.ffmpeg'], capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        print(e.stderr, file=sys.stderr)
        sys.exit(1)

def encodeoo(source_file, target_file, profile, **kwargs):
    properties = util.get_media_properties()

    profile_options = properties[profile + '.cmdline']
    if target_file is None:
        target_file = build_target_file(source_file, profile, properties)

    file_o = VideoFile(source_file)
    parms = file_o.get_ffmpeg_params()
    util.debug(1, "File settings = %s" % str(parms))
    parms.update(util.get_cmdline_params(profile_options))
    util.debug(1, "Profile settings = %s" % str(parms))
    parms.update(cmdline_options(**kwargs))
    util.debug(1, "Cmd line settings = %s" % str(parms))

    cmd = "%s -i %s %s %s" % (util.get_ffmpeg(), source_file, build_ffmpeg_options(parms), target_file)
    util.debug(1, "Running %s" % cmd)
    os.system(cmd)

def encode_album_art(source_file, album_art_file, **kwargs):
    """Encodes album art image in an audio file after optionally resizing"""
    # profile = 'album_art' - # For the future, we'll use the cmd line associated to the profile in the config file
    properties = util.get_media_properties()
    target_file = util.add_postfix(source_file, 'album_art')

    if kwargs['scale'] is not None:
        w, h = re.split("x",kwargs['scale'])
        album_art_file = rescale(source_file, w, h)
        delete_aa_file = True

    # ffmpeg -i %1 -i %2 -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover"
    # -metadata:s:v comment="Cover (Front)" %1.mp3
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

def rescale(image_file, width, height, out_file = None):
    properties = util.get_media_properties()
    if out_file is None:
        out_file = util.add_postfix(image_file, "%dx%d" % (width,height))
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

def deshake(video_file, width, height, out_file = None):
    ''' Applies deshake video filter for width x height pixels '''
    properties = util.get_media_properties()
    if out_file is None:
        out_file = util.add_postfix(video_file, "deshake_%dx%d" % (width,height))
    cmd = "%s -i %s %s -vcodec libx264 -deinterlace %s" % \
        (properties['binaries.ffmpeg'], video_file, get_deshake_filter_options(width, height), out_file)
    util.debug(1, "Running %s" % cmd)
    os.system(cmd)
    return out_file

def crop(video_file, width, height, top, left, out_file = None, **kwargs):
    file_o = VideoFile(video_file)
    return file_o.crop(width, height, top, left, out_file, **kwargs)

def probe_file(file):
    ''' Returns file probe (media specs) '''
    if util.is_media_file(file):
        try:
            properties = util.get_media_properties()
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
        specs['duration_hms'] = util.to_hms_str(stream['duration'])
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
    specs['duration_hms'] = util.to_hms_str(stream['duration'])
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



def get_mp3_tags(file):
    from mp3_tagger import MP3File
    if util.get_file_extension(file).lower() is not 'mp3':
        raise FileTypeError('File %s is not an mp3 file')
    # Create MP3File instance.
    mp3 = MP3File(file)
    return { 'artist' : mp3.artist, 'author' : mp3.artist, 'song' : mp3.song, 'title' : mp3.song, \
        'album' : mp3.album, 'year' : mp3.year, 'track' : mp3.track, 'genre' : mp3.genre, 'comment' : mp3.comment }

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
