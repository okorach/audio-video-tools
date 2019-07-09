#!/usr/local/bin/python3

'''Video file tools'''

from __future__ import print_function
import sys
import re
import os
import json
import shutil
import ffmpeg
import jprops
import mediatools.utilities as util
import mediatools.mediafile as media

class VideoFile(media.MediaFile):
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
        self.audio_language = None
        self.audio_sample_rate = None
        self.stream = None
        self.get_specs()

    def get_specs(self):
        '''Returns video file complete specs as dict'''
        if self.specs is None:
            self.probe()
            self.get_video_specs()
            self.get_audio_specs()

    def get_video_specs(self):
        '''Returns video file video specs as dict'''
        stream = self.get_video_stream()
        _, _ = self.get_dimensions(stream)
        _ = self.get_fps(stream)
        _ = self.get_video_codec(stream)
        try:
            self.video_bitrate = get_video_bitrate(stream)
            if self.video_bitrate is None:
                self.video_bitrate = self.specs['format']['bit_rate']
            self.duration = stream['duration']
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
                if 'codec_name' in stream:
                    self.audio_codec = stream['codec_name']
                if 'bit_rate' in stream:
                    self.audio_bitrate = stream['bit_rate']
                if 'sample_rate' in stream:
                    self.audio_sample_rate = stream['sample_rate']
                if 'tags' in stream and 'language' in stream['tags']:
                    self.audio_language = stream['tags']['language']
                    if self.audio_language in util.LANGUAGE_MAPPING:
                        self.audio_language = util.LANGUAGE_MAPPING[self.audio_language]
                break
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

    def get_video_codec(self, stream):
        '''Returns video file video codec'''
        util.debug(5, 'Getting video codec')
        if self.video_codec is None:
            if stream == None:
                stream = self.get_video_stream()
                util.debug(2, 'Video stream is %s' % json.dumps(stream, sort_keys=True, indent=3, separators=(',', ': ')))
            self.video_codec = stream['codec_name']
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

    def get_video_stream(self):
        util.debug(5, 'Searching video stream')
        for stream in self.specs['streams']:
            util.debug(5, 'Found codec %s / %s' % (stream['codec_type'], stream['codec_name']))
            if stream['codec_type'] == 'video' and stream['codec_name'] != 'gif':
                return stream
        return None

    def get_fps(self, stream = None):
        if self.video_fps is None:
            if stream == None:
                stream = self.get_video_stream()
                util.debug(5, 'Video stream is %s' % json.dumps(stream, sort_keys=True, indent=3, separators=(',', ': ')))
            for tag in [ 'avg_frame_rate', 'r_frame_rate']:
                if tag in stream:
                    self.video_fps = compute_fps(stream[tag])
                    break
        return self.video_fps

    def get_dimensions(self, stream = None):
        util.debug(5, 'Getting video dimensions')
        if self.width is None or self.height is None:
            if stream == None:
                stream = self.get_video_stream()
                util.debug(5, 'Video stream is %s' % json.dumps(stream, sort_keys=True, indent=3, separators=(',', ': ')))
        if self.width is None:
            for tag in [ 'width', 'codec_width', 'coded_width']:
                if tag in stream:
                    self.width = stream[tag]
                    break
        if self.height is None:
            for tag in [ 'height', 'codec_height', 'coded_height']:
                if tag in stream:
                    self.height = stream[tag]
                    break
        if self.width is not None and self.height is not None:
            self.pixels = self.width * self.height
        util.debug(5, "Returning %s, %s" % (str(self.width), str(self.height)))
        return [self.width, self.height]

        
    def get_audio_properties(self):
        if self.audio_codec is None:
            self.get_specs()
        return {'audio_bitrate': self.audio_bitrate, 'audio_codec': self.audio_codec, \
        'audio_language': self.audio_language, 'audio_sample_rate':self.audio_sample_rate }

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
        parms.update(media.cmdline_options(**clean_options))
        util.debug(1, "Cmd line settings = %s" % str(parms))

    def get_ffmpeg_params(self):
        mapping = { 'audio_bitrate':'b:a', 'audio_codec':'acodec', 'video_bitrate':'b:v', 'video_codec':'vcodec'}
        props = self.get_properties()
        ffmpeg_parms = {}
        for key in mapping:
            if props[key] is not None and props[key] is not '':
                ffmpeg_parms[mapping[key]] = props[key]
        return ffmpeg_parms

    def scale(self, scale):
        self.stream = ffmpeg.filter_(self.stream, 'scale', size=scale)

    def crop(self, width, height, top, left, out_file, **kwargs):
        ''' Applies crop video filter for width x height pixels '''
        parms = self.get_ffmpeg_params()
        clean_options = util.cleanup_options(kwargs)
        parms.update(media.cmdline_options(**clean_options))
        util.debug(1, "Cmd line settings = %s" % str(parms))
        out_file = util.automatic_output_file_name(out_file, self.filename, "crop_%dx%d-%dx%d" % (width, height, top, left))
        if 'aspect' not in kwargs:
            aw, ah = re.split(":", media.reduce_aspect_ratio(width, height))
        else:
            aw, ah = re.split(":", kwargs['aspect'])
        cmd = '%s -i "%s" %s %s -aspect %d:%d "%s"' % (util.get_ffmpeg(), self.filename, \
            media.build_ffmpeg_options(parms), media.get_crop_filter_options(width, height, top, left), \
            int(aw), int(ah), out_file)
        util.run_os_cmd(cmd)
        return out_file

    def cut(self, start, stop, out_file = None, **kwargs):
        parms = self.get_ffmpeg_params()
        kwargs['start'] = start
        kwargs['stop'] = stop
        parms.update(media.cmdline_options(**kwargs))

        util.debug(1, "Cmd line settings = %s" % str(parms))
        out_file = util.automatic_output_file_name(out_file, self.filename, "cut_%s-to-%s" % (start, stop))
        cmd = '%s -i "%s" %s "%s"' % (util.get_ffmpeg(), self.filename, \
            media.build_ffmpeg_options(parms), out_file)
        util.run_os_cmd(cmd)
        return out_file

    def deshake(self, width, height, out_file, **kwargs):
        ''' Applies deshake video filter for width x height pixels '''
        parms = self.get_ffmpeg_params()
        clean_options = util.cleanup_options(kwargs)
        parms.update({'deinterlace':'', 'aspect':self.get_aspect_ratio()})
        parms.update(media.cmdline_options(**clean_options))

        if out_file is None or 'nocrop' in kwargs:
            output_file = util.add_postfix(self.filename, "deshake_%dx%d" % (width, height))
        else:
            output_file = out_file
        cmd = '%s -i "%s" %s %s "%s"' % (util.get_ffmpeg(), self.filename, \
            media.build_ffmpeg_options(parms), get_deshake_filter_options(width, height), output_file)
        util.run_os_cmd(cmd)
        if 'nocrop' not in kwargs:
            return output_file

        new_w = self.get_width() - width
        new_h = self.get_height() - height
        if out_file is None:
            output_file2 = util.add_postfix(self.filename, "deshake_crop_%dx%d" % (new_w, new_h))
        else:
            output_file2 = out_file
        deshake_file_o = VideoFile(output_file)
        kwargs.update({'aspect': self.get_aspect_ratio()})
        deshake_file_o.crop(new_w, new_h, width//2, height//2, output_file2, **kwargs)
        os.remove(output_file)
        return output_file2

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

def encode(source_file, target_file, profile, **kwargs):
    properties = util.get_media_properties()
    if target_file is None:
        target_file = build_target_file(source_file, profile, properties)

    stream = ffmpeg.input(source_file)
    parms = util.get_profile_params(profile)
    parms.update(media.cmdline_options(**kwargs))

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
        print(e.message) # , file=sys.stderr)
        sys.exit(1)

def encodeoo(source_file, target_file, profile, **kwargs):
    properties = util.get_media_properties()

    profile_options = properties[profile + '.cmdline']
    if target_file is None:
        target_file = build_target_file(source_file, profile, properties)

    parms = {}
    if util.is_video_file(source_file):
        parms = VideoFile(source_file).get_ffmpeg_params()
        util.debug(2, "File settings = %s" % str(parms))

    parms.update(util.get_cmdline_params(profile_options))
    util.debug(2, "Profile settings = %s" % str(parms))
    parms.update(media.cmdline_options(**kwargs))
    util.debug(2, "Cmd line settings = %s" % str(parms))
    
    # Hack for channels selection
    if 'achannels' in kwargs and kwargs['achannels'] is not None:
        mapping = "-map 0:v:0"
        for channel in kwargs['achannels'].split(','):
            mapping += " -map 0:a:%s" % channel
    else:
        mapping = ""
    
    cmd = '%s -i "%s" %s %s "%s"' % (util.get_ffmpeg(), source_file, media.build_ffmpeg_options(parms), mapping, target_file)
    util.run_os_cmd(cmd)


def get_crop_filter_options(width, height, top, left):
    # ffmpeg -i in.mp4 -filter:v "crop=out_w:out_h:x:y" out.mp4
    return "-filter:v crop=%d:%d:%d:%d" % (width, height, top, left)

def get_deshake_filter_options(width, height):
    # ffmpeg -i <in> -f mp4 -vf deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=16 -b:v 2048k <out>
    return "-vf deshake=x=-1:y=-1:w=-1:h=-1:rx=%d:ry=%d" % (width, height)

def deshake(video_file, width, height, out_file = None, **kwargs):
    ''' Applies deshake video filter for width x height pixels '''
    file_o = VideoFile(video_file)
    return file_o.deshake(width, height, out_file, **kwargs)

def crop(video_file, width, height, top, left, out_file = None, **kwargs):
    file_o = VideoFile(video_file)
    return file_o.crop(width, height, top, left, out_file, **kwargs)


def compute_fps(rate):
    ''' Simplifies the FPS calculation '''
    util.debug(2, 'Calling compute_fps(%s)' % rate)
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

def get_mp3_tags(file):
    from mp3_tagger import MP3File
    if util.get_file_extension(file).lower() is not 'mp3':
        raise media.FileTypeError('File %s is not an mp3 file')
    # Create MP3File instance.
    mp3 = MP3File(file)
    return { 'artist' : mp3.artist, 'author' : mp3.artist, 'song' : mp3.song, 'title' : mp3.song, \
        'album' : mp3.album, 'year' : mp3.year, 'track' : mp3.track, 'genre' : mp3.genre, 'comment' : mp3.comment }

def concat(target_file, file_list):
    '''Concatenates several video files - They must have same video+audio format and bitrate'''
    util.debug(1, "%s = %s" % (target_file, ' + '.join(file_list)))
    cmd = util.get_ffmpeg()
    for file in file_list:
        cmd += (' -i "%s" ' % file)
    count = 0
    cmd += '-filter_complex "'
    for file in file_list:
        cmd += ("[%d:v] [%d:a]" % (count, count))
        count += 1
    cmd += 'concat=n=%d:v=1:a=1 [v] [a]" -map "[v]" -map "[a]" "%s"' % (count, target_file)
    util.run_os_cmd(cmd)
