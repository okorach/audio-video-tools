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

import os
import sys
import mediatools.utilities as util
import mediatools.file as fil
import mediatools.audiofile as audio


def main():
    me = sys.argv.pop(0)
    dir = None
    master_dir = None
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif arg == "-m":
            master_dir = sys.argv.pop(0)
        elif arg == "-d":
            dir = sys.argv.pop(0)
        else:
            sys.argv.pop(0)
    if dir is None or master_dir is None:
        print('Usage: {} [-g <debug_level>] <directory>', me)
        sys.exit(1)

    filelist = fil.dir_list(master_dir, recurse=True)
    hashes = audio.get_hash_list(filelist)
    collection = fil.dir_list(dir, recurse=False)

    for file in collection:
        if fil.is_link(file):
            continue
        h = audio.AudioFile(file).hash('audio')
        if h is None:
            util.logger.warning("Can't hash %s", file)
            continue
        if h not in hashes.keys():
            util.logger.warning("Can't find master file for %s", file)
            continue
        srcfile = fil.File(hashes[h][0])
        srcfile.create_link(dir + os.sep + srcfile.basename(ext='mp3'))

    sys.exit(0)


if __name__ == "__main__":
    main()
