#!/usr/local/bin/python3

import sys
import os
import mediatools.utilities as util
import mediatools.mediafile as media
import mediatools.videofile as video
import mediatools.version as version

def main():
    files = []
    util.set_logger('video-slideshow')
    resolution = media.Resolution.DEFAULT_VIDEO
    sys.argv.pop(0)
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif arg == "--resolution":
            resolution = sys.argv.pop(0)
        else:
            files.append(arg)
    if len(files) > 0:
        output = video.slideshow(files, resolution=resolution)
        util.logger.info("slideshow v%s - File %s generated", version.MEDIA_TOOLS_VERSION, output)
    else:
        util.logger.error("No inputs files could be used for slideshow, no slideshow generated")


if __name__ == "__main__":
    main()