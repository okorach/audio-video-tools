
import mediatools.utilities as util

class FfmpegOpts:
    FORMAT_OPTION = 'f'
    SIZE_OPTION = 's'
    VCODEC_OPTION = 'vcodec'
    ACODEC_OPTION = 'acodec'
    VBITRATE_OPTION = 'b:v'
    ABITRATE_OPTION = 'b:a'
    SIZE_OPTION = 's'
    FPS_OPTION = 'r'
    ASPECT_OPTION = 'aspect'
    DEINTERLACE_OPTION = 'deinterlace'
    ACHANNEL_OPTION = 'ac'
    VFILTER_OPTION = 'vf'
    START_OPTION = 'ss'
    STOP_OPTION = 'to'

class Encoder:
    '''Encoder abstraction'''
    SETTINGS = ['format', 'vcodec', 'vbitrate', 'acodec', 'abitrate', 'fps', 'aspect', \
                'vsize', 'deinterlace', 'achannel', 'asample', 'vfilter', 'start', 'stop']

    def __init__(self, **kwargs):
        self.format = None
        self.aspect = None
        self.video_codec = 'copy'
        self.video_bitrate = None
        self.video_fps = None
        self.audio_bitrate = None
        self.audio_codec = 'copy'
        self.audio_language = None
        self.audio_sample_rate = None
        self.start = None
        self.stop = None
        self.add_settings(**kwargs)

    def add_settings(self, **kwargs):
        kwsettings = {}
        for k in kwargs:
            if k in SETTINGS and kwargs[k] is not None:
                kwsettings[k] = kwargs[k]
        if 'vcodec' in kwsettings:
            self.vcodec = kwsettings['vcodec']
        if 'vbitrate' in kwsettings:
            self.video_bitrate = kwsettings['vbitrate']
        if 'acodec' in kwsettings:
            self.audio_codec = kwsettings['audio_codec']
        if 'abitrate' in kwsettings:
            self.audio_bitrate = kwsettings['audio_bitrate']
        if 'aspect' in kwsettings:
            self.aspect = kwsettings['aspect']
        if 'size' in kwsettings:
            self.size = kwsettings['size']
        if 'start' in kwsettings:
            self.start = kwsettings['start']
        if 'stop' in kwsettings:
            self.start = kwsettings['stop']
        if 'format' in kwsettings:
            self.format = kwsettings['format']

    def set_format(self, fmt):
        self.format = fmt

    def add_vfilter(self, filter):
        # -filter:v
        self.vfilters.append(filter)

    def add_crop_filter(self, width, height, top, left):
        self.add_vfilter("crop={0}:{1}:{2}:{3}".format(width, height, top, left))

    def add_deshake_filter(self, width, height):
    # ffmpeg -i <in> -f mp4 -vf deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=16 -b:v 2048k <out>
        self.add_vfilter("deshake=x=-1:y=-1:w=-1:h=-1:rx={0}:ry={1}}".format(width, height))

    def add_fade_filter(self, fade_duration, start, stop):
        if start is None:
            start = self.start
        if stop is None:
            stop = self.stop
        if start is not None and stop is not None:
            self.add_vfilter("fade=type=in:duration={0}:start_time={1},fade=type=out:duration={2}:start_time={3}". \
                    format(fade_duration, util.to_seconds(start), fade_duration, util.to_seconds(stop)-fade_duration))
        else:
            self.add_vfilter("fade=type=in:duration={0},fade=type=out:duration={1}:start_time={2}". \
                    format(fade_duration, fade_duration, stop-fade_duration))

    def ffmpeg_opts(self):
        opts = ''
        if self.start is not None:
            opts = opts + '-{0} {1}'.format(FfmpegOpts.START_OPTION, self.start)
        if self.stop is not None:
            opts = opts + '-{0} {1}'.format(FfmpegOpts.STOP_OPTION, self.start)
        if self.size is not None:
            opts = opts + '-{0} {1}'.format(FfmpegOpts.SIZE_OPTION, self.size)
        if self.video_codec is not None:
            opts = opts + '-{0} {1}'.format(FfmpegOpts.VCODEC_OPTION, self.video_codec)
        if self.video_bitrate is not None:
            opts = opts + '-{0} {1}'.format(FfmpegOpts.VBITRATE_OPTION, self.video_bitrate)
        if self.audio_codec is not None:
            opts = opts + '-{0} {1}'.format(FfmpegOpts.ACODEC_OPTION, self.audio_codec)
        if self.audio_bitrate is not None:
            opts = opts + '-{0} {1}'.format(FfmpegOpts.ABITRATE_OPTION, self.audio_bitrate)
        if self.video_fps is not None:
            opts = opts + '-{0} {1}'.format(FfmpegOpts.FPS_OPTION, self.video_fps)
        if self.format is not None:
            opts = opts + '-{0} {1}'.format(FfmpegOpts.FORMAT_OPTION, self.format)

