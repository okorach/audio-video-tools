#!/usr/local/bin/python3

import sys
import os
import mediatools.utilities as util
import mediatools.audiofile as audio
import mediatools.imagefile as image

DEFAULT_RESCALING = '512x512'

def filelist_poster(filelist, bg):
    image.posterize(filelist, None, bg)

def dir_poster(directory, bg):
    filelist = util.filelist(directory)
    filelist_poster(filelist, bg)

file_list = []
dir_list = []
bg = "black"
sys.argv.pop(0) # Remove script name
while len(sys.argv) > 0:
    arg = sys.argv.pop(0)
    if arg == "-g":
        util.set_debug_level(sys.argv.pop(0))
    elif arg is "-background":
        bg = sys.argv.pop(0)
    elif os.path.isdir(arg):
        dir_list.append(arg)
    else:
        util.debug(1, "Appending file %s" % arg)
        file_list.append(arg)

for directory in dir_list:
    dir_poster(directory)

if len(file_list) > 0:
    filelist_poster(file_list, bg)
