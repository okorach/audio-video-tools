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
from typing import Optional
import concurrent.futures
from mediatools import utilities as util, log, audiofile as audio
from utilities import file as fil


def get_csv_values(file) -> Optional[list[str]]:
    if not fil.is_audio_file(file):
        return None
    log.logger.info("Getting file '%s' metadata", file)
    f = audio.AudioFile(file)
    if str(f.get_a_tag("album")).lower() == "Album":
        f.set_tag("album", "")
    return f.csv_values()


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
    filelist = fil.dir_list(directory, recurse=True)
    nb_files = len(filelist)
    cur_file = 0
    with open("music.csv", "w", newline="", encoding="utf-8") as fh:
        csv_writer = csv.writer(fh, dialect="excel", quoting=csv.QUOTE_MINIMAL)
        print(audio.csv_headers())
        with concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="GetMetadata") as executor:
            futures = [executor.submit(get_csv_values, file) for file in fil.dir_list(directory, recurse=True)]
            for future in concurrent.futures.as_completed(futures):
                data = future.result(timeout=10)
                log.logger.debug("Got data %s", data)
                if data is not None:
                    csv_writer.writerow(data)
                cur_file += 1
                log.logger.info("Processed %d of %d files (%d%%)", cur_file, nb_files, (cur_file * 100) // nb_files)

    sys.exit(0)


if __name__ == "__main__":
    main()
