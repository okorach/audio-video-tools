# media-tools
# Copyright (C) 2021 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import mediatools.utilities as util
import mediatools.exceptions as ex
import mediatools.file as fil
import mediatools.audiofile as audio
import mediatools.videofile as video


def __patch_args(file_type, **kwargs):
    if file_type == fil.FileType.VIDEO_FILE and 'vcodec' not in kwargs:
        kwargs['vcodec'] = 'copy'
        kwargs['hw_accel'] = False
    if 'acodec' not in kwargs:
        kwargs['acodec'] = 'copy'
        kwargs['hw_accel'] = False
    if kwargs['acodec'] == 'copy' or kwargs.get('vcodec', None) == 'copy':
        for o in ('abitrate', 'vbitrate', 'fps', 'aspect', 'resolution', 'achannels', 'samplerate', 'width', 'height'):
            kwargs.pop(o, None)
    return kwargs

def cut(file, output=None, start=None, stop=None, timeranges=None, **kwargs):
    t = fil.get_type(file)
    if t not in (fil.FileType.VIDEO_FILE, fil.FileType.AUDIO_FILE):
        raise ex.FileTypeError(file, 'video or audio')
    kwargs = __patch_args(t, **kwargs)
    if t == fil.FileType.AUDIO_FILE:
        file_object = audio.AudioFile(file)
    elif t == fil.FileType.VIDEO_FILE:
        file_object = video.VideoFile(file)
        kwargs['vcodec'] = 'copy'
        kwargs.pop('vbitrate', None)
    kwargs['acodec'] = 'copy'
    kwargs.pop('abitrate', None)
    if start is None and stop is None:
        i = 1
        for r in timeranges.split(','):
            kwargs['start'], kwargs['stop'] = r.split('-', maxsplit=2)
            outputfile = util.automatic_output_file_name(outfile=output, infile=file, postfix=f'cut{i}')
            outputfile = file_object.encode(target_file=outputfile, **kwargs)
            util.generated_file(outputfile)
            i += 1
    else:
        if start is None:
            start = 0
        if stop is None:
            stop = file_object.duration
        outputfile = util.automatic_output_file_name(outfile=output, infile=file, postfix='cut')
        outputfile = file_object.encode(target_file=outputfile, start=start, stop=stop, **kwargs)
        util.generated_file(outputfile)
    return output
