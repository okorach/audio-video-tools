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

import argparse
import mediatools.exceptions as ex
import mediatools.utilities as util
import mediatools.creator as creator
import mediatools.options as opt

STD_FMT = "%-20s : %s"

VIDEO_PROPS = ['filename', 'filesize', 'type',
    opt.Option.FORMAT, opt.Option.WIDTH, opt.Option.HEIGHT, opt.Option.DURATION,
    opt.Option.VCODEC, opt.Option.VBITRATE, opt.Option.ASPECT, 'pixel_aspect_ratio', opt.Option.FPS,
    opt.Option.ACODEC, opt.Option.ABITRATE, opt.Option.LANGUAGE, opt.Option.ASAMPLING, opt.Option.AUTHOR]

AUDIO_PROPS = ['filename', 'filesize', 'type', opt.Option.FORMAT, opt.Option.DURATION,
    opt.Option.ACODEC, opt.Option.ABITRATE, opt.Option.ASAMPLING,
    opt.Option.AUTHOR, opt.Option.TITLE, opt.Option.ALBUM, opt.Option.YEAR, opt.Option.TRACK, opt.Option.GENRE]

IMAGE_PROPS = ['filename', 'filesize', 'type',
    opt.Option.FORMAT, opt.Option.WIDTH, opt.Option.HEIGHT, 'pixels', opt.Option.AUTHOR, opt.Option.TITLE]

UNITS = {'filesize': 'bytes', opt.Option.DURATION: 'time', opt.Option.VBITRATE: 'bits/s',
        opt.Option.ABITRATE: 'bits/s', opt.Option.ASAMPLING: 'bits', 'pixels': 'pix'}


def __to_csv__(specs, all_props):
    s = ''
    for prop in all_props:
        if prop not in specs:
            s += ','
        else:
            s += str(specs[prop]) + ','
        if prop == 'duration':
            s += util.to_hms(specs[prop], fmt='string') + ','
    return s[:-1]


def __to_std__(specs, all_props):
    s = ''
    for prop in sorted(all_props):
        if prop not in specs:
            continue
        u = ''
        v = specs[prop]
        if prop not in UNITS:
            s += "{}: {} {}\n".format("%-20s" % prop, v, u)
            continue
        if UNITS[prop] in ('bytes', 'bits', 'pix', 'bytes/s', 'bits/s'):
            v = float(v)
            if v > 1024 * 1024 * 1024:
                v = round(v / 1024 / 1024 / 1024, 2)
                u = 'G' + UNITS[prop]
            elif v > 1024 * 1024:
                v = round(v / 1024 / 1024, 2)
                u = 'M' + UNITS[prop]
            elif v > 1024:
                v = round(v / 1024, 2)
                u = 'k' + UNITS[prop]
            else:
                u = UNITS[prop]
        elif UNITS[prop] == 'time':
            v = util.to_hms(specs[prop], fmt='string')
        s += "{}: {} {}\n".format("%-20s" % prop, v, u)
    return s[:-1]


def main():
    parser = argparse.ArgumentParser(description='Audio/Video/Image file specs extractor')
    parser.add_argument('-i', '--inputfile', required=True, help='Input file or directory to probe')
    parser.add_argument('-f', '--format', required=False, default='txt', help='Output file format (txt or csv)')
    parser.add_argument('-t', '--types', required=False, default='',
                        help='Types of files to include [audio,video,image]')
    parser.add_argument('-g', '--debug', required=False, default=0, help='Debug level')
    parser.add_argument('--dry_run', required=False, default=0, help='Dry run mode')
    kwargs = util.parse_media_args(parser)

    filelist = util.file_list(kwargs['inputfile'])

    all_props = list(set(VIDEO_PROPS + AUDIO_PROPS + IMAGE_PROPS))

    fmt = kwargs['format']
    if fmt == 'csv':
        print("# ")
        for prop in all_props:
            print("%s," % prop, end='')
            if prop == 'duration':
                print("%s," % "Duration HH:MM:SS.x", end='')
        print('')

    for file in filelist:
        try:
            file_object = creator.file(file)
        except ex.FileTypeError:
            continue
        specs = file_object.get_properties()
        util.logger.debug("Specs = %s", util.json_fmt(specs))
        if fmt == 'csv':
            print(__to_csv__(specs, all_props))
        else:
            print(__to_std__(specs, all_props))


if __name__ == "__main__":
    main()
