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

import os
import re
import argparse
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.audiofile as audio
import mediatools.mediafile as media
import mediatools.imagefile as img
import mediatools.options as opt

STD_FMT = "%-20s : %s"

VIDEO_PROPS = ['filename', 'filesize', 'type',
    opt.media.FORMAT, opt.media.WIDTH, opt.media.HEIGHT, opt.media.DURATION,
    opt.media.VCODEC, opt.media.VBITRATE, opt.media.ASPECT, 'pixel_aspect_ratio', opt.media.FPS,
    opt.media.ACODEC, opt.media.ABITRATE, opt.media.LANGUAGE, opt.media.ASAMPLING, opt.media.AUTHOR]

AUDIO_PROPS = ['filename', 'filesize', 'type', opt.media.FORMAT, opt.media.DURATION,
    opt.media.ACODEC, opt.media.ABITRATE, opt.media.ASAMPLING,
    opt.media.AUTHOR, opt.media.TITLE, opt.media.ALBUM, opt.media.YEAR, opt.media.TRACK, opt.media.GENRE]

IMAGE_PROPS = ['filename', 'filesize', 'type',
    opt.media.FORMAT, opt.media.WIDTH, opt.media.HEIGHT, 'pixels', opt.media.AUTHOR, opt.media.TITLE]

UNITS = {'filesize': [1048576, 'MB'], opt.media.DURATION: [1, 'hms'], opt.media.VBITRATE: [1024, 'kbits/s'],
        opt.media.ABITRATE: [1024, 'kbits/s'], opt.media.ASAMPLING: [1000, 'k'], 'pixels': [1000000, 'Mpix']}


def file_list(input_item, filetypes=''):
    filelist = []
    if os.path.isdir(input_item):
        if filetypes == '':
            types = ['video', 'audio', 'image']
        else:
            types = re.split(',', filetypes.lower())
        if 'video' in types:
            filelist.extend(util.video_filelist(input_item))
        if 'audio' in types:
            filelist.extend(util.audio_filelist(input_item))
        if 'image' in types:
            filelist.extend(util.image_filelist(input_item))
    else:
        filelist = [input_item]
    return filelist


def main():
    parser = argparse.ArgumentParser(description='Audio/Video/Image file specs extractor')
    parser.add_argument('-i', '--inputfile', required=True, help='Input file or directory to probe')
    parser.add_argument('-f', '--format', required=False, default='txt', help='Output file format (txt or csv)')
    parser.add_argument('-t', '--types', required=False, default='',
                        help='Types of files to include [audio,video,image]')
    parser.add_argument('-g', '--debug', required=False, default=0, help='Debug level')
    parser.add_argument('--dry_run', required=False, default=0, help='Dry run mode')
    args = parser.parse_args()
    options = vars(args)
    util.check_environment(options)
    util.cleanup_options(options)

    filelist = file_list(args.inputfile)

    all_props = list(set(VIDEO_PROPS + AUDIO_PROPS + IMAGE_PROPS))

    if args.format == 'csv':
        print("# ")
        for prop in all_props:
            print("%s;" % prop, end='')
            if prop == 'duration':
                print("%s;" % "Duration HH:MM:SS", end='')
        print('')

    props = all_props
    nb_files = len(filelist)
    for file in filelist:
        try:
            if not util.is_media_file(file):
                raise media.FileTypeError("File %s is not a supported file format" % file)
            if util.is_video_file(file):
                file_object = video.VideoFile(file)
                if nb_files == 1:
                    props = VIDEO_PROPS
            elif util.is_audio_file(file):
                file_object = audio.AudioFile(file)
                if nb_files == 1:
                    props = AUDIO_PROPS
            elif util.is_image_file(file):
                file_object = img.ImageFile(file)
                if nb_files == 1:
                    props = IMAGE_PROPS

            specs = file_object.get_properties()
            util.logger.debug("Specs = %s", util.json_fmt(specs))
            for prop in props:
                if args.format != "csv":
                    try:
                        if prop in UNITS:
                            (divider, unit) = UNITS[prop]
                            if unit == 'hms':
                                print(STD_FMT % (prop, util.to_hms_str(specs[prop])))
                            else:
                                print("%-20s : %.1f %s" % (prop, (int(specs[prop]) / divider), unit))
                        else:
                            print(STD_FMT % (prop, str(specs[prop]) if specs[prop] is not None else ''))
                    except KeyError:
                        print(STD_FMT % (prop, ""))
                    except TypeError:
                        print(STD_FMT % (prop, "Wrong type"))
                else:
                    # CSV format
                    try:
                        print("%s;" % (str(specs[prop]) if specs[prop] is not None else ''), end='')
                        if prop == 'duration':
                            print("%s;" % util.to_hms_str(specs[prop]), end='')
                    except KeyError:
                        print("%s;" % '', end='')
            print("")
        except media.FileTypeError as e:
            print('ERROR: File %s type error %s' % (file, str(e)))


if __name__ == "__main__":
    main()
