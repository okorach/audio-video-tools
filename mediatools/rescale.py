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

'''
This script rescale an image to different dimension
It can also rescale all the images of a given directory
Pass rescale dimensions as -s WxH
'''

import mediatools.imagefile as image
import mediatools.utilities as util


def __int_or_empty(x):
    if x == "":
        return -1
    else:
        return int(x)


def main():
    parser = util.get_common_args('image-scale', 'Rescale image dimensions of a file or directory')
    kwargs = util.parse_media_args(parser)
    outputfile = image.ImageFile(kwargs['inputfiles']).scale(
        kwargs.get('width', -1), kwargs.get('height', -1), out_file=kwargs.get('outputfile', None))

    print('Generated', outputfile)


if __name__ == "__main__":
    main()
