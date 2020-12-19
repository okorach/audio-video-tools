#!/usr/local/bin/python3

import sys
import mediatools.utilities as util
import mediatools.videofile as video


def main():
    util.set_logger('video-slideshow')
    util.set_debug_level(5)
    sys.argv.pop(0)
    output = video.slideshow(sys.argv, resolution="1280x720")
    util.logger.info("File %s generated", output)

if __name__ == "__main__":
    main()