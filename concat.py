#!/usr/local/bin/python3

import videotools.filetools, videotools.videofile
import sys
import os

videotools.filetools.set_debug_level(0)

sys.argv.pop(0)
target_file = sys.argv.pop()

filelist = []
for file in sys.argv:
    filelist.append(file)

videotools.videofile.concat(target_file, filelist)