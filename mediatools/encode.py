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

import mediatools.file as fil
import mediatools.videofile as video
import mediatools.utilities as util
import mediatools.options as opt


def encode_file(file, **kwargs):
    '''Encodes a single file'''
    file_object = video.VideoFile(file)
    if kwargs.get('width', None) is not None:
        specs = file_object.get_properties()
        w = int(specs[opt.Option.WIDTH])
        h = int(specs[opt.Option.HEIGHT])
        new_w = int(kwargs['width'])
        if kwargs.get('vheight', None) is not None:
            new_h = int(kwargs.get('vheight', 0))
        else:
            new_h = (int(h * new_w / w) // 8) * 8
        kwargs[opt.Option.SIZE] = "%dx%d" % (new_w, new_h)
    if kwargs.get('timeranges', None) is None:
        file_object.encode(kwargs.get('outputfile', None), **kwargs)
        return

    if kwargs.get('outputfile', None) is None:
        ext = util.get_profile_extension(kwargs.get('profile'))
    count = 0
    filelist = []
    timeranges = kwargs.get('timeranges', None).split(',')
    for video_range in timeranges:
        kwargs[opt.Option.START], kwargs[opt.Option.STOP] = video_range.split('-')
        count += 1
        target_file = util.automatic_output_file_name(kwargs.get('outputfile', None), file, str(count), ext)
        filelist.append(target_file)
        outputfile = file_object.encode(target_file, **kwargs)
        util.logger.info("File %s generated", outputfile)
        print("File %s generated", outputfile)
    if len(timeranges) > 1:
        # If more than 1 file generated, concatenate all generated files
        target_file = util.automatic_output_file_name(kwargs.get('outputfile', None), file, "combined", ext)
        video.concat(target_file, filelist)
        util.logger.info("Concatenated file %s generated", target_file)
        print("Concatenated file %s generated", target_file)


def main():
    parser = util.get_common_args('video-encode', 'Audio and Video file (re)encoder')
    parser = video.add_video_args(parser)
    kwargs = util.parse_media_args(parser)

    file_list = util.file_list(kwargs['inputfile'], file_type=fil.FileType.VIDEO_FILE)
    nb_files = len(file_list)
    for i in range(nb_files):
        util.logger.info("%3d/%3d : %3d%% : %s", i + 1, nb_files, (i + 1) * 100 // nb_files, file_list[i])
        encode_file(file_list[i], **kwargs)


if __name__ == "__main__":
    main()
