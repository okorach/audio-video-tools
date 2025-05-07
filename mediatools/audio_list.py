#!python3
#
# media-tools
# Copyright (C) 2022 Olivier Korach
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
import csv
import mediatools.utilities as util
from mediatools import log
import utilities.file as fil
import mediatools.audiofile as audio


def main():
    util.init("audio-list")
    me = sys.argv.pop(0)
    directory = None
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif os.path.isdir(arg):
            directory = arg
    if directory is None:
        print(f"Usage: {fil.basename(me)} [-g <debug_level>] <directory>")
        sys.exit(1)
    with open("music.csv", "w", newline="", encoding="utf-8") as fh:
        csv_writer = csv.writer(fh, dialect="excel", quoting=csv.QUOTE_MINIMAL)
        print(audio.csv_headers())
        for file in fil.dir_list(directory, recurse=True):
            if not fil.is_audio_file(file):
                continue
            log.logger.info("Outputting file: %s", file)
            f = audio.AudioFile(file)
            if str(f.get_a_tag("album")).lower() == "Album":
                f.set_tag("album", "")
            csv_writer.writerow(f.csv_values())
    sys.exit(0)


if __name__ == "__main__":
    main()
