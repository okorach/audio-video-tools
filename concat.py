#!/usr/local/bin/python3

import sys
import mediatools.utilities as util
import mediatools.videofile as video

util.set_debug_level(2)

sys.argv.pop(0)
target_file = sys.argv.pop()

filelist = []
for file in sys.argv:
    filelist.append(file)

video.concat(target_file, filelist)
