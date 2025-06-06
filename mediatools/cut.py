#!python3
#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
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

"""
This script cuts a video or audio file
"""

import sys
from mediatools import log
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.avfile as av


MISSING_PARAM = """--start and --stop or --timeranges options is mandatory,
type media-cut -h for more details"""


def main():
    parser = util.get_common_args("media-cut", "Cuts a time window of the input video file")
    parser = video.add_video_args(parser)
    parser.add_argument("--start", required=False, help="Cut start timestamp")
    parser.add_argument("--stop", required=False, help="Cut stop timestamp")
    kwargs = util.parse_media_args(parser)
    if kwargs.get("timeranges", None) is not None:
        log.logger.info("Getting multiple ranges")
        ranges = kwargs.get("timeranges", None)
        if ranges is None:
            log.logger.error(MISSING_PARAM)
            sys.exit(1)
    else:
        log.logger.info("Getting single start/stop range")
        ranges = f"{kwargs.get('start', '')}-{kwargs.get('stop', '')}"
    i = 0
    last_stop = 0
    log.logger.info("Ranges = %s", str(ranges))
    t_ranges = ranges.split(",")
    ifile = kwargs.pop("inputfiles")
    log.logger.info("t_Ranges = %s", str(t_ranges))
    for time_interval in t_ranges:
        i += 1
        log.logger.info("Cutting range %s", time_interval)
        t_bounds = time_interval.split("-")
        log.logger.info("t_bounds = %s len = %d", str(t_bounds), len(t_bounds))
        if len(t_bounds) == 2:
            (start, stop) = t_bounds
            outputfile = util.automatic_output_file_name(outfile=None, infile=ifile, postfix=f"cut{i}")
            log.logger.info("Generating file %s", outputfile)
            av.cut(ifile, output=outputfile, start=start, stop=stop)
            last_stop = stop
            if i == len(t_ranges):
                i += 1
                outputfile = util.automatic_output_file_name(outfile=None, infile=ifile, postfix=f"cut{i}")
                av.cut(ifile, output=outputfile, start=start, stop=stop)
        else:
            log.logger.info("Generating single cut")
            av.cut(ifile, output=kwargs.get("outputfile", None), **kwargs)


if __name__ == "__main__":
    main()
