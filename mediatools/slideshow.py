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

import sys
import os
import json
from mediatools import log
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.media_config as conf

def _dump_report_(report, file):
    if file is None:
        f = sys.stdout
        log.logger.info("Dumping report to stdout")
        print(json.dumps(report, indent=4, sort_keys=False, separators=(',', ': ')))
    else:
        with open(file, "w") as f:
            log.logger.info("Dumping report to file '%s'", file)
            print(json.dumps(report, indent=4, sort_keys=False, separators=(',', ': ')), file=f)

def main():
    files = []
    util.init('video-slideshow')
    resolution = conf.get_property('video.default.resolution')
    me = sys.argv.pop(0).split(os.sep)[-1]
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif arg == "--resolution":
            resolution = sys.argv.pop(0)
        elif arg[0] == "-":
            print(f"Usage: {me} [-g <LEVEL>] [-h] [--resolution WxH] <file1> ... <filen>")
            sys.exit(1)
        else:
            files.append(arg)
    if files:
        (output, operations) = video.slideshow(*files, resolution=resolution)
        json_file = output + '.json'
        _dump_report_(operations, json_file)
        msg = f"File {output} generated, report is {json_file}"
        log.logger.info(msg)
        print(msg)
    else:
        log.logger.error("No inputs files could be used for slideshow, no slideshow generated")


if __name__ == "__main__":
    main()
