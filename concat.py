#!/usr/local/bin/python3

import mediatools.utilities, mediatools.videofile
import sys
import os

mediatools.utilities.set_debug_level(0)

sys.argv.pop(0)
target_file = sys.argv.pop()

filelist = []
for file in sys.argv:
    filelist.append(file)

mediatools.videofile.concat(target_file, filelist)