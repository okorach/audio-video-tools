#!/usr/local/bin/python3

import sys
import os
import mediatools.utilities as util
import mediatools.audiofile as audio
import mediatools.imagefile as image

DEFAULT_RESCALING = '512x512'

def filelist_poster(filelist, bg, margin):
    image.posterize(filelist, None, bg, margin)

def dir_poster(dirname, bg, margin):
    filelist = util.filelist(dirname)
    filelist_poster(filelist, bg, margin)

file_list = []
dir_list = []
background = "black"
margin=5
sys.argv.pop(0)
while sys.argv:
    arg = sys.argv.pop(0)
    if arg == "-g":
        util.set_debug_level(sys.argv.pop(0))
    elif arg == "--background":
        background = sys.argv.pop(0)
    elif arg == "--dry_run":
        util.set_dry_run(True)
    elif arg == "--bottom":
        bottom = sys.argv.pop(0)
    elif arg == "--top":
        top = sys.argv.pop(0)
    elif arg == "--left":
        left = sys.argv.pop(0)
    elif arg == "--right":
        left = sys.argv.pop(0)
    elif arg == "--margin":
        margin = int(sys.argv.pop(0))
    elif os.path.isdir(arg):
        dir_list.append(arg)
    else:
        util.logger.info("Adding file %s to poster", arg)
        file_list.append(arg)

for directory in dir_list:
    dir_poster(directory, background, margin)

if file_list:
    filelist_poster(file_list, background, margin)
