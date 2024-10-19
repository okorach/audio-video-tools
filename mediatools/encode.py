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

# This script encodes a video file according to (by order of precedence):
# - Script command line options
# - Profile specs (from config file)
# - Original file specs (audio/video codec and bitrate)

import os
from mediatools import log
import utilities.file as fil
import mediatools.videofile as video
import mediatools.audiofile as audio
import mediatools.utilities as util
import mediatools.options as opt
import utilities.file as fileutil

def encode_file(file, file_type, **kwargs):
    '''Encodes a single file'''
    if file_type == fil.FileType.AUDIO_FILE:
        file_object = audio.AudioFile(file)
    else:
        file_object = video.VideoFile(file)
        # if kwargs.get('width', None) is not None:
        #     specs = file_object.get_properties()
        #     w, h = int(specs[opt.Option.WIDTH]), int(specs[opt.Option.HEIGHT])
        #     new_w = int(kwargs['width'])
        #     if kwargs.get('vheight', None) is not None:
        #         new_h = int(kwargs.get('vheight', 0))
        #     else:
        #         new_h = (int(h * new_w / w) // 8) * 8
        #     kwargs[opt.Option.RESOLUTION] = f"{new_w}x{new_h}"

    if kwargs.get('timeranges', None) is None:
        outfile = file_object.encode(kwargs.get('outputfile', None), **kwargs)
        video.set_creation_date(outfile, video.get_creation_date(file))
        return outfile


    ext = util.get_profile_extension(kwargs.get('profile'))
    count = 0
    filelist = []
    timeranges = kwargs.get('timeranges', None).split(',')
    creation_date = video.get_creation_date(file)
    for t_r in timeranges:
        kwargs[opt.Option.START], kwargs[opt.Option.STOP] = t_r.split('-')
        count += 1
        target_file = util.automatic_output_file_name(None, file, str(count), ext)
        filelist.append(target_file)
        outputfile = file_object.encode(target_file, **kwargs)
        log.logger.info("File %s generated", outputfile)
        video.set_creation_date(outputfile, creation_date)

        print(f"File {outputfile} generated")

    if len(timeranges) > 1:
        # If more than 1 file generated, concatenate all generated files
        target_file = kwargs.get('outputfile', None)
        if target_file is None:
            target_file = util.automatic_output_file_name(target_file, file, "combined", ext)
        video.concat(target_file, filelist)
        log.logger.info("Concatenated file %s generated", target_file)
        video.set_creation_date(target_file, creation_date)
        print(f"Concatenated file {target_file} generated")
    return target_file


def main():
    parser = util.get_common_args('video-encode', 'Audio and Video file (re)encoder')
    parser = video.add_video_args(parser)

    kwargs = util.parse_media_args(parser)

    file_list = fil.file_list(kwargs['inputfile'])
    nb_files = len(file_list)
    for i in range(nb_files):
        log.logger.info("%3d/%3d : %3d%% : %s", i + 1, nb_files, (i + 1) * 100 // nb_files, file_list[i])
        ofile = encode_file(file_list[i], fil.get_type(file_list[i]), **kwargs)
        if kwargs.get("keepName", False):
            splits = file_list[i].split(".")
            ext = splits.pop()
            base = ".".join(splits)
            fileutil.rename(file_list[i], f"{base}.before_encode.{ext}", False)
            fileutil.rename(ofile, file_list[i])


if __name__ == "__main__":
    main()
