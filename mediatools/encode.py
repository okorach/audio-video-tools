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

# This script encodes a video file according to (by order of precedence):
# - Script command line options
# - Profile specs (from config file)
# - Original file specs (audio/video codec and bitrate)

"""Tool that encodes audio and video files with an encoding profile"""

from __future__ import annotations

import mediatools.audiofile as audio
import mediatools.options as opt
import mediatools.utilities as util
import mediatools.videofile as video
import utilities.file as fil
from mediatools import log


def encode_file(file: str, file_type: str, **kwargs: object) -> str:
    """Encodes a single file"""
    if file_type == fil.FileType.AUDIO_FILE:
        file_object = audio.AudioFile(file)
    elif file_type == fil.FileType.VIDEO_FILE:
        file_object = video.VideoFile(file)
    else:
        raise ValueError(f"File {file} is not an audio or video file")

    if kwargs.get("timeranges") is None:
        outfile = file_object.encode(kwargs.get(util.OUTPUT_FILE), **kwargs)
        video.set_creation_date(outfile, video.get_creation_date(file))
        return outfile

    ext = util.get_encoding_extension(file, kwargs.get("profile"), kwargs.get("format"))
    count = 0
    filelist: list[str] = []
    timeranges = kwargs.get("timeranges").split(",")
    creation_date = video.get_creation_date(file)
    for count, t_r in enumerate(timeranges, start=1):
        kwargs[opt.Option.START], kwargs[opt.Option.STOP] = t_r.split("-")
        target_file = util.automatic_output_file_name(None, file, str(count), ext)
        filelist.append(target_file)
        outputfile = file_object.encode(target_file, **kwargs)
        log.logger.info("File %s generated", outputfile)
        video.set_creation_date(outputfile, creation_date)

        print(f"File {outputfile} generated")

    if len(timeranges) > 1:
        # If more than 1 file generated, concatenate all generated files
        target_file = kwargs.get(util.OUTPUT_FILE)
        if target_file is None:
            target_file = util.automatic_output_file_name(target_file, file, "combined", ext)
        video.concat(target_file, filelist)
        log.logger.info("Concatenated file %s generated", target_file)
        video.set_creation_date(target_file, creation_date)
        print(f"Concatenated file {target_file} generated")
    return target_file


def main() -> None:
    """Encodes audio and video files with an encoding profile"""
    parser = util.get_common_args("video-encode", "Audio and Video file (re)encoder")
    parser = video.add_video_args(parser)

    kwargs = util.parse_media_args(parser, input_type=(fil.FileType.AUDIO_FILE, fil.FileType.VIDEO_FILE))

    file_list = kwargs[util.INPUT_FILES]
    nb_files = len(file_list)
    progress = util.GlobalProgress(nb_files)
    for i in range(nb_files):
        log.logger.info("%3d/%3d : %3d%% : %s", i + 1, nb_files, (i + 1) * 100 // nb_files, file_list[i])
        ofile = encode_file(file_list[i], fil.get_type(file_list[i]), **kwargs)
        if kwargs.get("keepName", False) and fil.extension(ofile).lower() == fil.extension(file_list[i]).lower():
            splits = file_list[i].split(".")
            ext = splits.pop()
            base = ".".join(splits)
            fil.rename(file_list[i], f"{base}.original.{ext}", False)
            fil.rename(ofile, file_list[i])
        progress.done()


if __name__ == "__main__":
    main()
