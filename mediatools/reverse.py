#!/usr/local/bin/python3

import sys
import mediatools.utilities as util
import mediatools.videofile as video

def main():
    util.set_logger('video-reverse')
    hw_accel = False
    sys.argv.pop(0)
    while sys.argv:
        arg = sys.argv.pop(0)
        if arg == "-g":
            util.set_debug_level(sys.argv.pop(0))
        elif arg == "--hw_accel":
            hw_accel = True
        elif util.is_video_file(arg):
            output = video.VideoFile(arg).reverse(hw_accel=hw_accel)
            util.logger.info("File %s generated", output)

if __name__ == "__main__":
    main()