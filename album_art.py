#!python

import videotools.filetools, videotools.videofile
import sys

album_art = None
for file in sys.argv:
    if videotools.filetools.is_image_file(file):
        album_art = file

if album_art is None:
    print('Album Art image file not found')
    exit(1)
else:
    print('Encoding Album Art image file %s' % album_art)

for file in sys.argv:
    if videotools.filetools.is_audio_file(file):
        print('Encoding audio file %s' % file)
        videotools.videofile.encode_album_art(file, album_art)
