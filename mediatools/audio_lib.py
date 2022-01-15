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
from pathlib import Path
from mediatools import log
import mediatools.utilities as util
import mediatools.file as fil
import mediatools.audiofile as audio

def search_on_other_drives(file):
    for drive_letter in ('C', 'D', 'E', 'F'):
        new_file = f"{drive_letter}{file[1:]}"
        log.logger.debug("Checking existence of %s", new_file)
        if os.path.isfile(new_file):
            log.logger.debug("Found %s", new_file)
            return new_file
    log.logger.debug("Found no file")
    return None


def __check_file_name(file):
    if not fil.is_audio_file(file):
        return
    f = audio.AudioFile(file)
    p = Path(file)
    new_name = f"{p.parent}{os.sep}{f.title} - {f.artist}.{fil.extension(file)}"
    if new_name == file:
        return
    try:
        os.rename(file, new_name)
    except FileExistsError:
        pass


def __fix_symlink(symlink, target_file):
    old_tgt = target_file
    log.logger.info("Trying to fix symlink %s --> Target = %s", symlink, old_tgt)
    target_file = search_on_other_drives(old_tgt)
    if target_file is None:
        log.logger.error("Can't find target %s for file %s", symlink, old_tgt)
    else:
        os.remove(symlink)
        fil.create_link(target_file, symlink)
    return target_file


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
        print(f'Usage: {fil.basename(me)} [-g <debug_level>] <directory>')
        sys.exit(1)
    for symlink in fil.dir_list(directory, recurse=False):
        if not fil.is_link(symlink):
            __check_file_name(symlink)
            continue
        tgt = fil.read_link(symlink)
        if not os.path.isfile(tgt):
            tgt = __fix_symlink(tgt, symlink)
        log.logger.info("Symlink %s --> Target = %s", symlink, tgt)
        f = audio.AudioFile(tgt)
        # tags = f.get_tags()
        # if 'title' in tags and 'artist' in tags:
        #     base = "{} - {}".format(tags['title'], tags['artist'])
        # elif 'title' in tags:
        #     base = tags['title']
        # else:
        #     base = tgt.split(os.path.sep)[-1]
        if f.title is None or f.artist is None:
            log.logger.warning("Can't copy file because %s has empty title or artist", tgt)
        else:
            shutil.copy(tgt, directory + os.path.sep + f.title + " - " + f.artist + ".mp3")
    sys.exit(0)


if __name__ == "__main__":
    main()
