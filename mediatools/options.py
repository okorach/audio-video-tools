class ff:
    FORMAT = 'f'
    SIZE = 's'
    VCODEC = 'vcodec'
    ACODEC = 'acodec'
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
    media.START:ff.STOP \
    }

F2M_MAPPING = {}
for k, v in M2F_MAPPING.items():
    F2M_MAPPING[v] = k