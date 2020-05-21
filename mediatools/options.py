import mediatools.utilities as util

'''
This file encapsulates
- various constants
- data structures and
- translation functions
used in several places
in mediatools library
'''

class ff:
    '''Documents supported ffmpeg options'''
    FORMAT = 'f'
    SIZE = 's'
    VCODEC = 'vcodec'
    VCODEC2 = 'c:v'
    VCODEC3 = 'codec:v'
    ACODEC = 'acodec'
    ACODEC2 = 'c:a'
    ACODEC3 = 'codec:a'
    VBITRATE = 'b:v'
    ABITRATE = 'b:a'
    SIZE = 's'
    FPS = 'r'
    ASPECT = 'aspect'
    DEINTERLACE = 'deinterlace'
    ACHANNEL = 'ac'
    VFILTER = 'vf'
    START = 'ss'
    STOP = 'to'

class media:
    '''Documents supported audio-video-tools encoding options'''
    FORMAT = 'format'
    SIZE = 'vsize'
    VCODEC = 'vcodec'
    ACODEC = 'acodec'
    VBITRATE = 'vbitrate'
    ABITRATE = 'abitrate'
    WIDTH = 'width'
    HEIGHT = 'height'
    FPS = 'fps'
    ASPECT = 'aspect'
    DEINTERLACE = 'deinterlace'
    ACHANNEL = 'achannels'
    VFILTER = 'vfilter'
    START = 'start'
    STOP = 'stop'
    ASAMPLING = 'asamplerate'
    AUTHOR = 'author'
    TITLE = 'title'
    ALBUM = 'album'
    YEAR = 'year'
    TRACK = 'track'
    GENRE = 'genre'
    DURATION = 'duration'
    LANGUAGE = 'language'

M2F_MAPPING = { \
    media.FORMAT:ff.FORMAT, \
    media.VCODEC:ff.VCODEC, \
    media.VBITRATE:ff.VBITRATE, \
    media.ACODEC:ff.ACODEC, \
    media.ABITRATE:ff.ABITRATE, \
    media.FPS:ff.FPS, \
    media.ASPECT:ff.ASPECT, \
    media.SIZE:ff.SIZE, \
    media.DEINTERLACE:ff.DEINTERLACE, \
    media.ACHANNEL:ff.ACHANNEL, \
    media.VFILTER:ff.VFILTER, \
    media.START:ff.START, \
    media.STOP:ff.STOP \
    }

F2M_MAPPING = {}
for k, v in M2F_MAPPING.items():
    F2M_MAPPING[v] = k
F2M_MAPPING[ff.ACODEC2] = media.ACODEC
F2M_MAPPING[ff.ACODEC3] = media.ACODEC
F2M_MAPPING[ff.VCODEC2] = media.VCODEC
F2M_MAPPING[ff.VCODEC3] = media.VCODEC

def media2ffmpeg(options):
    # Returns ffmpeg cmd options dict from media options dict
    if options is None:
        return {}
    ffopts = {}
    for key in M2F_MAPPING:
        if key in options and options[key] is not None:
            ffopts[M2F_MAPPING[key]] = options[key]
    return util.remove_nones(ffopts)

def ffmpeg2media(options):
    # Returns ffmpeg cmd options dict from media options dict
    if options is None:
        return {}
    mopts = {}
    for key in M2F_MAPPING:
        if key in options and options[key] is not None:
            mopts[M2F_MAPPING[key]] = options[key]
    return util.remove_nones(mopts)
