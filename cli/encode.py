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

from __future__ import annotations

import os
import sys

from mediatools import log
from mediatools import videofile as vf
import mediatools.utilities as util
import utilities.file as fil


def set_and_parse_cli_args() -> dict:
    """Initializes the logs, defines the command line options of the encoder and returns the parsed options"""
    util.init("encode")
    parser = util.get_common_args("encode", "ffmpeg front-end encoder")
    parser = vf.add_video_args(parser)
    return util.parse_media_args(parser)


def build_file_name(file: str, postfix: str, ext: str = "mp4") -> str:
    """Returns the name of an output file: the input name with a postfix (and a sequence number if the file already exists) and the extension"""
    pieces = file.split(".")
    pieces.pop()
    base = ".".join(pieces)
    if not os.path.exists(f"{base}.{postfix}.{ext}"):
        return f"{base}.{postfix}.{ext}"
    seq = 1
    while os.path.exists(f"{base}.{postfix}.{seq}.{ext}"):
        seq += 1
    return f"{base}.{postfix}.{seq}.{ext}"


def main() -> None:
    """Encodes the audio and video files given on the command line, one after the other"""
    kwargs = set_and_parse_cli_args()
    files_to_encode = kwargs.pop(util.INPUT_FILES)
    files_to_encode = [f for f in files_to_encode if fil.is_media_file(f)]
    log.logger.info("Filtered files (%d)", len(files_to_encode))
    postfix = ""
    if "width" in kwargs:
        postfix += "." + str(kwargs["width"]) + "px"
    if "vbitrate" in kwargs:
        postfix += "." + kwargs["vbitrate"]
    if "quality" in kwargs:
        postfix += "." + kwargs["quality"]
    if "vcodec" in kwargs:
        postfix += "." + kwargs["vcodec"]
    if "fps" in kwargs:
        postfix += "." + kwargs["fps"] + "fps"
    if postfix == "":
        postfix = "encoded"
    else:
        postfix = postfix[1:]
    for ifile in files_to_encode:
        ofile = build_file_name(ifile, postfix)
        vf.VideoFile(ifile).encode(target_file=ofile, profile=None, **kwargs)
        vf.set_creation_date(ofile, vf.get_creation_date(ifile))
        if kwargs.get("keepName", False):
            splits = ifile.split(".")
            ext = splits.pop()
            base = ".".join(splits)
            fil.rename(ifile, f"{base}.original.{ext}", False)
            fil.rename(ofile, ifile)
    sys.exit(0)


if __name__ == "__main__":
    main()
