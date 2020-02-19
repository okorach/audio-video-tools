
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

OPTIONS_MAPPING = { 'format':FfmpegOpts.FORMAT_OPTION, \
   'vcodec':FfmpegOpts.VCODEC_OPTION, 'vbitrate':FfmpegOpts.VBITRATE_OPTION, \
   'acodec':FfmpegOpts.ACODEC_OPTION, 'abitrate':FfmpegOpts.ABITRATE_OPTION, \
   'fps':FfmpegOpts.FPS_OPTION, 'aspect':FfmpegOpts.ASPECT_OPTION, 'vsize':FfmpegOpts.SIZE_OPTION, \
   'deinterlace':FfmpegOpts.DEINTERLACE_OPTION, 'achannel':FfmpegOpts.ACHANNEL_OPTION, \
   'vfilter':FfmpegOpts.VFILTER_OPTION, \
   'start': FfmpegOpts.START_OPTION, 'stop': FfmpegOpts.STOP_OPTION }

LANGUAGE_MAPPING = { 'fre': 'French', 'eng': 'English'}

class Encoder:
    '''Encoder abstraction'''
    SETTINGS = ['format', 'vcodec', 'vbitrate', 'acodec', 'abitrate', 'fps', 'aspect', \
                'vsize', 'deinterlace', 'achannel', 'asample', 'vfilter', 'start', 'stop']

    def __init__(self, **kwargs):
        self.format = None
        self.aspect = None
        self.size = None
        self.video_codec = 'copy'
        self.video_bitrate = None
        self.video_fps = None
        self.audio_bitrate = None
        self.audio_codec = 'copy'
        self.audio_language = None
        self.audio_sample_rate = None
        self.start = None
        self.stop = None
        self.vfilters = []
        self.add_settings(**kwargs)
        self.other_options = {}

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

    def add_vfilter(self, vfilter):
        self.vfilters.append(vfilter)

    def get_vfilters_string(self):
        cmd = ''
        for f in self.vfilters:
            cmd = cmd + '-filter:v "%s" ' % f
        return cmd.strip()

    def add_crop_filter(self, width, height, top, left):
        self.add_vfilter("crop={0}:{1}:{2}:{3}".format(width, height, top, left))

    def add_deshake_filter(self, width, height):
    # ffmpeg -i <in> -f mp4 -vf deshake=x=-1:y=-1:w=-1:h=-1:rx=16:ry=16 -b:v 2048k <out>
        self.add_vfilter("deshake=x=-1:y=-1:w=-1:h=-1:rx={0}:ry={1}".format(width, height))

    def add_fade_filter(self, fade_d, start = None, stop = None):
        if start is None: start = self.start
        if start is None: start = 0
        if stop is None: stop = self.stop
        fmt = "fade=type={0}:duration={1}:start_time={2}"
        fader = fmt.format('in', fade_d, start) + "," + fmt.format('out', fade_d, stop - fade_d)
        self.add_vfilter(fader)

    def ffmpeg_opts(self):
        '''Builds string corresponding to ffmpeg conventions'''
        options = vars(self)
        cmd = ''
        for option in options.keys():
            if options[option] is not None and not isinstance(options[option], list):
                cmd = cmd + " -{0} {1}".format(OPTIONS_MAPPING[option], options[option])
        cmd = cmd + ' ' + self.get_vfilters_string()
        return cmd.strip()

