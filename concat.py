#!/usr/local/bin/python3

# This script concatenate 2 video files
# They should have the same video and audio codecs and bitrates

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