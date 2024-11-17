#!python3
#
# media-tools
# Copyright (C) 2024 Olivier Korach
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

import os
import sys
import re

from random import randrange
from pathlib import Path
from mediatools import log
from mediatools import videofile as vf
import mediatools.utilities as util
import utilities.file as fil
import mediatools.audiofile as audio


def set_and_parse_cli_args() -> dict[str, str]:
    util.init('encode')
    parser = util.get_common_args("encode", "ffmpeg front-end encoder")
    parser = vf.add_video_args(parser)
    #parser.add_argument('-I', '--inputfiles', metavar='N', type=str, nargs='+', help='List of files to encode')
    return util.parse_media_args(parser)


def get_expanded_file_list(file_list: list[str]) -> list[str]:
    expanded_list = []
    for file in file_list:
        if os.path.isdir(file):
            expanded_list += fil.dir_list(file, recurse=False)
        else:
            expanded_list.append(file)
    return expanded_list

def build_file_name(file: str, postfix: str, ext: str = "mp4") -> str:
    pieces = file.split(".")
    # ext = pieces.pop()
    base = ".".join(pieces)
    if not os.path.exists(f"{base}.{postfix}.{ext}"):
        return f"{base}.{postfix}.{ext}"
    seq = 1
    while os.path.exists(f"{base}.{postfix}.{seq}.{ext}"):
        seq += 1
    return f"{base}.{postfix}.{seq}.{ext}"

def main():
    kwargs = set_and_parse_cli_args()
    files_to_encode = get_expanded_file_list(kwargs.pop("inputfiles"))
    files_to_encode = [f for f in files_to_encode if fil.is_media_file(f)]
    log.logger.info("Filtered files (%d)", len(files_to_encode))
    # nb_files = len(files_to_encode)
    postfix = ""
    if "vbitrate" in kwargs:
        postfix += kwargs["vbitrate"]
    if "vcodec" in kwargs:
        postfix += "." + kwargs["vcodec"]
    if "fps" in kwargs:
        postfix += "." + kwargs["fps"] + "fps"
    if postfix == "":
        postfix = "encoded"
    for ifile in files_to_encode:
        ofile = build_file_name(ifile, postfix)
        vf.VideoFile(ifile).encode(target_file=ofile, profile=None, **kwargs)

    sys.exit(0)


if __name__ == "__main__":
    main()
