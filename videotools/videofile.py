
#!python3

import sys
import ffmpeg

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
            stderr, stdout = ffmpeg.run(self.stream)
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
        return ffmpeg.probe(self.name)

    def set_author(self, author):
        self.author = author

    def get_author(self):
        return self.author

    def set_copyright(self, copyright):
        self.copyright = copyright

    def get_copyright(self):
        return self.copyright



