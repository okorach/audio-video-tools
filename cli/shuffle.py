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
import re
import shutil
from random import randrange
from pathlib import Path
import argparse
from mediatools import log
import mediatools.utilities as util
import mediatools.file as fil
import mediatools.audiofile as audio


def main():
    util.init('audio-shuffle')
    parser = argparse.ArgumentParser(description='Shuffle audio files with random numeric prefix')
    parser.add_argument('-i', '--inputfiles', metavar='N', type=str, nargs='+', help='List of files to shuffle')
    parser.add_argument('-g', '--debug', required=False, type=int, help='Debug level')
    kwargs = util.parse_media_args(parser)
    me = sys.argv.pop(0)
    files_to_shuffle = []
    for file in kwargs["inputfiles"]:
        if os.path.isdir(file):
            files_to_shuffle += fil.dir_list(file, recurse=False)
        else:
            files_to_shuffle.append(file)

    log.logger.info("Unfiltered files (%d)", len(files_to_shuffle))
    files_to_shuffle = [f for f in files_to_shuffle if fil.is_audio_file(f)]
    log.logger.info("Filtered files (%d)", len(files_to_shuffle))
    nb_files = len(files_to_shuffle)
    seq = 0
    while len(files_to_shuffle) > 0:
        file = files_to_shuffle.pop(randrange(len(files_to_shuffle)))
        dirname = fil.dirname(file)
        basename = fil.basename(file)
        ext = fil.extension(basename)
        prefix = fil.strip_extension(basename)
        pieces = prefix.split('.')
        i = 0
        for p in pieces:
            if not re.match(r"^[ 0-9]+$", p):
                break
            i += 1

        prefix = ".".join([s.strip() for s in pieces[i:]])
        seq += 1
        if nb_files < 10:
            str_seq = f"{seq:01}"
        elif nb_files < 100:
            str_seq = f"{seq:02}"
        elif nb_files < 1000:
            str_seq = f"{seq:03}"
        else:
            str_seq = f"{seq}"
        os.rename(file, f"{dirname}{os.sep}{str_seq}. {prefix}.{ext}")

    sys.exit(0)


if __name__ == "__main__":
    main()
