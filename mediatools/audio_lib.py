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
import shutil
import mediatools.log as log
import mediatools.utilities as util
import mediatools.file as fil
import mediatools.audiofile as audio


def main():
    util.init('audio-lib')
    me = sys.argv.pop(0)
    directory = None
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif os.path.isdir(arg):
            directory = arg
    if directory is None:
        print('Usage: {} [-g <debug_level>] <directory>', me)
        sys.exit(1)
    for file in fil.dir_list(directory, recurse=False):
        if not fil.is_link(file):
            continue
        tgt = fil.get_symlink_target(file)
        log.logger.info("Symlink %s --> Target = %s", file, tgt)
        f_audio = audio.AudioFile(tgt)
        # tags = f_audio.get_tags()
        # if 'title' in tags and 'artist' in tags:
        #     base = "{} - {}".format(tags['title'], tags['artist'])
        # elif 'title' in tags:
        #     base = tags['title']
        # else:
        #     base = tgt.split(os.path.sep)[-1]
        base = "{} - {}.mp3".format(f_audio.title, f_audio.artist)
        log.logger.info("Copy to = %s", dir + os.path.sep + base)
        shutil.copy(tgt, dir + os.path.sep + base)
    sys.exit(0)


if __name__ == "__main__":
    main()
