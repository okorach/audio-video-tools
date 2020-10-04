#!/usr/local/bin/python3

# This script applies the ffmpeg deshake filter on a video file
# to improve image stabilization

import re
import argparse
import mediatools.utilities as util
import mediatools.videofile as video

def parse_args():
    parser = util.parse_common_args(desc='Apply deshake filter')
    parser = video.add_video_args(parser)
    parser.add_argument('--width', required=True, help='Deshake width')
    parser.add_argument('--height', required=True, help='Deshake height')
    parser.add_argument('--nocrop', required=False, help='Do not crop video after deshaking')
    return parser.parse_args()


def main():
    args = parse_args()
    kwargs = vars(args)
    util.check_environment(kwargs)
    kwargs = util.cleanup_options(kwargs)
    del kwargs['width']
    del kwargs['height']
    if args.timeranges is not None:
        for video_range in re.split(',', args.timeranges):
            kwargs['ss'], kwargs['to'] = re.split('-', video_range)
    outputfile = video.deshake(args.inputfile, int(args.width), int(args.height), args.outputfile, **kwargs)
    util.debug(1, 'Generated %s' % outputfile)


if __name__ == "__main__":
    main()

