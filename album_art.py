#!python

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
    album_art_file = find_image(filelist)
    if album_art_file is None:
        util.debug(0, "No image file in directory %" % directory)
    else:
        filelist_album_art(filelist, album_art_file)

filelist = []
album_art_file = None
for file in sys.argv:
    if os.path.isdir(file):
        dir_album_art(file)
    elif util.is_image_file(file):
        album_art_file = file
    else:
        filelist.append(file)
if album_art_file is None:
    util.debug(0, "No image file found in %s" % str(sys.argv))
else:
    filelist_album_art(filelist, album_art_file)

