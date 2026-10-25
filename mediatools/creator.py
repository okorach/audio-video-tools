#
# media-tools
# Copyright (C) 2019-2026 Olivier Korach
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

"""Factory of the media file objects (audio, video or image)"""

from __future__ import annotations

import mediatools.audiofile as audio
import mediatools.exceptions as ex
import mediatools.imagefile as image
import mediatools.mediafile as media
import mediatools.videofile as video
import utilities.file as fil


def file(filename: str) -> media.MediaFile:
    """Returns the media file object (audio, video or image) for a file. Raises a FileTypeError for any other file"""
    if fil.is_audio_file(filename):
        return audio.AudioFile(filename)
    if fil.is_video_file(filename):
        return video.VideoFile(filename)
    if fil.is_image_file(filename):
        return image.ImageFile(filename)
    raise ex.FileTypeError(file=filename)
