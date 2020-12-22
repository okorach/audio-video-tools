#!/usr/local/bin/python3

import sys
import mediatools.utilities as util
import mediatools.videofile as video

DEFAULT_RESOLUTION = "1280x720"

def main():
    files = []
    util.set_logger('video-slideshow')
    resolution = DEFAULT_RESOLUTION
    sys.argv.pop(0)
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif arg == "--resolution":
            resolution = sys.argv.pop(0)
        elif not util.is_image_file(arg):
            util.logger.error("File %s does not exist or is not an image file, skipped...", arg)
        else:
            files.append(arg)
    if len(files) > 0:
        output = video.slideshow(files, resolution=resolution)
        util.logger.info("File %s generated", output)
    else:
        util.logger.error("No inputs files could be used for slideshow, no slideshow generated")


if __name__ == "__main__":
    main()