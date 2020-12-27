#!python3
#
# media-tools
# Copyright (C) 2019-2020 Olivier Korach
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

import mediatools.exceptions as ex
import mediatools.utilities as util
import mediatools.audiofile as audio
import mediatools.videofile as video
import mediatools.imagefile as image


def file(filename):
    if util.is_audio_file(filename):
        return audio.AudioFile(filename)
    elif util.is_video_file(filename):
        return video.VideoFile(filename)
    elif util.is_image_file(filename):
        return image.ImageFile(filename)
    else:
        raise ex.FileTypeError(file=filename)

