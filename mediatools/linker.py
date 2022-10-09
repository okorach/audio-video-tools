#!python3
#
# media-tools
# Copyright (C) 2019-2022 Olivier Korach
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
import argparse
from mediatools import log
import mediatools.utilities as util
import mediatools.file as fil
import mediatools.audiofile as audio


def link_file(file, directory, hash_data):
    hashes = hash_data["hashes"]
    if fil.is_link(file) or not fil.is_audio_file(file):
        return None
    h = audio.AudioFile(file).hash('audio')
    if h is None:
        log.logger.warning("Can't hash %s", file)
        return None
    log.logger.debug("Hash for %s is %s", file, h)
    if h not in hashes.keys():
        log.logger.warning("Can't find master file for %s", file)
        return None
    srcfile = audio.AudioFile(hashes[h][0])
    srcfile.get_tags()
    base = "{}{}{} - {}".format(directory, os.sep, srcfile.title, srcfile.artist)
    srcfile.create_link(base)
    return directory + os.sep + base

def copy_file(file, directory, hash_data):
    if not fil.is_link(file) or not fil.is_audio_file(file):
        return None
    shortcut = fil.File(file)
    srcfile = shortcut.read_link()
    targetfile = directory + os.sep + fil.basename(srcfile)
    shutil.copyfile(srcfile, targetfile)
    return targetfile

def main():
    util.init('audio-linker')
    directory = None
    master_dir = None
    parser = argparse.ArgumentParser(description='Manages audio collections')
    parser.add_argument('-m', '--master', help='master audio directory', required=True)
    parser.add_argument('-d', '--directory', help='directory with collection', required=True)
    parser.add_argument('-u', '--updateHash', action="store_true", default=False, help='ask to update hash of master directory', required=False)
    parser.add_argument('-l', '--linkFiles', action="store_true", default=False, help='ask to link files of collection directory', required=False)
    parser.add_argument('-c', '--copyFiles', action="store_true", default=False, help='ask to copy files linked from master directory', required=False)
    parser.add_argument('-a', '--all', action="store_true", default=False, help='Do everything', required=False)
    parser.add_argument('-g', '--debug', required=False, type=int, help='Debug level')
    kwargs = util.parse_media_args(parser)

    master_dir = kwargs["master"]
    directory = kwargs["directory"]
    hash_file = f"{master_dir}.json"

    if not os.path.exists(hash_file) or kwargs["updateHash"]:
        log.logger.info("Rebuilding file hash")
        hashes = audio.update_hash_list(master_dir)
        if kwargs["updateHash"]:
            sys.exit(0)
    else:
        log.logger.info("Reading existing hash")
        hashes = audio.read_hash_list(hash_file)
    log.logger.info("%d files in hash", len(hashes["hashes"]))
    collection = fil.dir_list(directory, recurse=False)

    if kwargs["linkFiles"]:
        for file in collection:
            link_file(file, directory, hashes)
    elif kwargs["copyFiles"]:
        for file in collection:
            copy_file(file, directory, hashes)
    elif kwargs["all"]:
        for file in collection:
            link_file(file, directory, hashes)
            copy_file(file, directory, hashes)

    sys.exit(0)


if __name__ == "__main__":
    main()
