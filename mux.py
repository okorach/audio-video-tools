#!/usr/local/bin/python3

import sys
import os
import mediatools.videofile as video
import mediatools.utilities as util

util.set_debug_level(5)
sys.argv.pop(0)
videofile = video.VideoFile(sys.argv.pop(0))
videofile.add_audio_tracks(*sys.argv)
