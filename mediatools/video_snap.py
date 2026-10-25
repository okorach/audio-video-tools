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

"""Snaps photos from videos, either n photos evenly spread in the video or one photo every given number of seconds."""

import math
import os
import sys
import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fileutil
from mediatools import log


def snap_times(duration: float, nbr_photos: int | None = None, every: float | None = None) -> list[float]:
    """Returns the timestamps (in seconds) of the photos to snap.
    With nbr_photos, the video is split in nbr_photos + 1 intervals and a photo is snapped at each of the nbr_photos boundaries.
    With every, a photo is snapped every <every> seconds until the end of the video is reached"""
    if nbr_photos is not None:
        return [duration * k / (nbr_photos + 1) for k in range(1, nbr_photos + 1)]
    count = math.ceil(duration / every) - 1  # Number of multiples of "every" strictly before the end
    return [every * k for k in range(1, count + 1)]


def photo_name(input_file: str, index: int, total: int, out_dir: str | None = None) -> str:
    """Returns the photo name for photo number index (from 1): foo.mp4 -> foo.1.jpg, foo.01.jpg if total > 9, foo.001.jpg if total > 99..."""
    base = os.path.splitext(os.path.basename(input_file))[0]
    directory = out_dir or os.path.dirname(input_file)
    return os.path.join(directory, f"{base}.{index:0{len(str(total))}d}.jpg")


def snap_file(input_file: str, nbr_photos: int | None = None, every: float | None = None, out_dir: str | None = None) -> list[str]:
    """Snaps the photos of a video file, returns the list of generated photos"""
    duration = video.get_duration(input_file)
    if not duration:
        raise ValueError(f"Can't get the duration of {input_file}")
    times = snap_times(duration, nbr_photos, every)
    if not times:
        log.logger.warning("No photo to snap in %s (duration %.2fs)", input_file, duration)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    photos = []
    for index, t in enumerate(times, start=1):
        photo = photo_name(input_file, index, len(times), out_dir)
        util.run_ffmpeg(f'-ss {t:.3f} -i "{input_file}" -frames:v 1 -q:v 2 "{photo}"')
        util.generated_file(photo)
        photos.append(photo)
    return photos


def main():
    parser = util.get_common_args("video-snap", "Snaps photos from videos")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--nbr_photos", type=int, help="Number of photos to snap, evenly spread in the video (the video is split in n+1 intervals)")
    group.add_argument("--every", type=float, help="Snap a photo every <every> seconds of the video, until its end")
    kwargs = util.parse_media_args(parser, input_type=fileutil.FileType.VIDEO_FILE)
    nbr_photos, every = kwargs.get("nbr_photos"), kwargs.get("every")
    if (nbr_photos is not None and nbr_photos <= 0) or (every is not None and every <= 0):
        log.logger.error("--nbr_photos and --every must be positive numbers")
        sys.exit(2)

    def process(input_file: str, options: dict) -> None:
        snap_file(input_file, nbr_photos, every, options.get(util.OUTPUT_FILE))

    util.process_input_files(kwargs, process)


if __name__ == "__main__":
    main()
