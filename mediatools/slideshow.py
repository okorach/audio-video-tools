#!/usr/local/bin/python3

import sys
import mediatools.utilities as util
import mediatools.videofile as video

def main():
    files = []
    util.set_logger('video-slideshow')
    util.set_debug_level(5)
    sys.argv.pop(0)
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif arg == "--resolution":
            resolution = sys.argv.pop(0)
        elif util.is_image_file(arg):
            files.append(arg)
    output = video.slideshow(files, resolution=resolution)
    util.logger.info("File %s generated", output)

if __name__ == "__main__":
    main()