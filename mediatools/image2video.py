#!/usr/local/bin/python3

import argparse
import mediatools.utilities as util
import mediatools.imagefile as image


def main():
    parser = util.parse_common_args('image2video')
    parser.add_argument('-e', '--effect', required=False, default="zoom", help='Effect to generate')
    parser.add_argument('-z', '--zoom_level', required=False, default=1.3, help='Zoom level for zoom in/out')
    parser.add_argument('--panorama', required=False, default="left", help='Type of panorama')
    parser.add_argument('--duration', required=False, default=5, help='Duration of video')
    parser.add_argument('--direction', required=False, default="left", help='Direction of the panorama')
    kwargs = vars(parser.parse_args())

    util.check_environment(kwargs)
    inputfile = kwargs.pop('inputfile')
    if kwargs['effect'] == "panorama":
        image.ImageFile(inputfile).panorama(resolution=kwargs['framesize'], duration=kwargs['duration'],
            direction=kwargs['direction'])
    else:
        image.ImageFile(inputfile).zoom_in(final_zoom=kwargs['zoom_level'], resolution=kwargs['framesize'])


if __name__ == "__main__":
    main()
