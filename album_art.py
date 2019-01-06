#!/usr/local/bin/python3

import sys
import os
import mediatools.utilities as util
import mediatools.audiofile as audio
import mediatools.imagefile as image

DEFAULT_RESCALING = '512x512'

def find_image(filelist):
    for file in filelist:
        if util.is_image_file(file):
            return file
    return None

def filelist_album_art(filelist, image_file):
    for file in filelist:
        if util.is_audio_file(file):
            util.debug(1, 'Encoding album art %s in file %s' % (image_file, file))
            audio.encode_album_art(file, image_file, **{'scale':DEFAULT_RESCALING})

def dir_album_art(directory):
    filelist = util.filelist(directory)
    dir_album_art_file = find_image(filelist)
    if album_art_file is None:
        util.debug(0, "No image file in directory %s" % directory)
    else:
        filelist_album_art(filelist, dir_album_art_file)

file_list = []
album_art_file = None
for file_arg in sys.argv:
    if os.path.isdir(file_arg):
        dir_album_art(file_arg)
    elif util.is_image_file(file_arg):
        album_art_file = file_arg
    else:
        file_list.append(file_arg)
if album_art_file is None:
    util.debug(0, "No image file found in %s" % str(sys.argv))
else:
    filelist_album_art(file_list, album_art_file)
