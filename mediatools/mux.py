#!/usr/local/bin/python3

# This script multiplexes an extra audio track
# in a video file with already one audio track

import sys
import os
import mediatools.videofile as video
import mediatools.utilities as util


def main():
    util.set_debug_level(5)
    afiles = []
    for i in range (0, len(sys.argv)):
        file = sys.argv[i]
        if util.is_video_file(file):
            vfile = file
            util.logger.info("Video file %s will be muxed", file)
        elif util.is_audio_file(file):
            util.logger.info("Audio file %s will be muxed", file)
            afiles.append(file)

    videofile = video.VideoFile(vfile)
    videofile.add_audio_tracks(*afiles)


if __name__ == "__main__":
    main()
