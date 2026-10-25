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

"""This script cuts a video or audio file"""

import sys
from mediatools import log
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.avfile as av
import utilities.file as fil

MISSING_PARAM = """--start and --stop or --timeranges options is mandatory,
type media-cut -h for more details"""


def main() -> None:
    """Cuts a part of audio and video files, between a start and a stop time or in time ranges"""
    parser = util.get_common_args("media-cut", "Cuts a time window of the input video file")
    parser = video.add_video_args(parser)
    parser.add_argument("--start", required=False, help="Cut start timestamp")
    parser.add_argument("--stop", required=False, help="Cut stop timestamp")
    kwargs = util.parse_media_args(parser, input_type=(fil.FileType.VIDEO_FILE, fil.FileType.AUDIO_FILE))
    timeranges = kwargs.get("timeranges")
    if timeranges is None and kwargs.get("start") is None and kwargs.get("stop") is None:
        log.logger.error(MISSING_PARAM)
        sys.exit(1)
    if timeranges is not None and len(timeranges.split(",")) > 1 and kwargs.get(util.OUTPUT_FILE):
        log.logger.error("-o can't be used with several time ranges")
        sys.exit(2)

    def process(ifile: str, options: dict) -> None:
        """Cuts a part of one audio or video file"""
        if timeranges is not None:
            # start and stop are those of the first time range, av.cut() cuts all the ranges
            options.pop("start", None)
            options.pop("stop", None)
        av.cut(ifile, output=options.pop(util.OUTPUT_FILE, None), **options)

    util.process_input_files(kwargs, process)


if __name__ == "__main__":
    main()
