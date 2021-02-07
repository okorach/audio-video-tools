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
import win32com.client
import mediatools.utilities as util
import mediatools.audiofile as audio
# import mediatools.media_config as conf


def main():
    me = sys.argv.pop(0)
    dir = None
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif os.path.isdir(arg):
            dir = arg
    if dir is None:
        print('Usage: {} [-g <debug_level>] <directory>', me)
        sys.exit(1)
    filelist = util.dir_list(dir, recurse=False)

    for file in filelist:
        if file.endswith('.lnk'):  # os.path.islink() does not work :-(
            util.logger.info("Checking %s: SYMLINK", file)

            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(file)
            tgt = shortcut.Targetpath

            util.logger.info("Target = %s", tgt)
            f_audio = audio.AudioFile(tgt)
            tags = f_audio.get_tags()
            util.logger.debug("TAGS = %s", util.json_fmt(tags))
            # if 'title' in tags and 'artist' in tags:
            #     base = "{} - {}".format(tags['title'], tags['artist'])
            # elif 'title' in tags:
            #     base = tags['title']
            # else:
            #     base = tgt.split(os.path.sep)[-1]
            base = "{} - {}.mp3".format(f_audio.title, f_audio.artist)
            util.logger.info("Copy to = %s", dir + os.path.sep + base)
            shutil.copy(tgt, dir + os.path.sep + base)
        else:
            util.logger.debug("Checking %s: Not a symlink", file)
    sys.exit(0)


if __name__ == "__main__":
    main()
