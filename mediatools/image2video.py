#!/usr/local/bin/python3

import argparse
import mediatools.utilities as util
import mediatools.imagefile as image

DEFAULT_RESOLUTION = "1280x720"

def main():
    parser = util.parse_common_args('image2video')
    parser.add_argument('-e', '--effect', required=False, default="zoom", help='Effect to generate')
    parser.add_argument('-z', '--zoom-effect', required=False, default=1.3, help='Zoom level for zoom in/out')
    parser.add_argument('--panorama-effect', required=False, default="left", help='Type of panorama')
    parser.add_argument('--duration', required=False, default=5, help='Duration of video')
    parser.add_argument('--direction', required=False, default="left", help='Direction of the panorama')
    kwargs = util.remove_nones(vars(parser.parse_args()))

    util.check_environment(kwargs)
    inputfile = kwargs.pop('inputfile')
    resolution = kwargs.get('framesize', DEFAULT_RESOLUTION)

    if kwargs['effect'] == "panorama":
        effect = kwargs.get('panorama-effect', "0.2,0.8,0.6,0.4").split(",")
        for i in range(len(effect)):
            effect[i] = float(effect[i])
        image.ImageFile(inputfile).panorama(resolution=resolution, duration=kwargs['duration'],
            effect=effect)
    else:
        effect = kwargs.get('zoom-effect', "100,130").split(",")
        for i in range(len(effect)):
            effect[i] = float(effect[i])
        image.ImageFile(inputfile).zoom(resolution=resolution, duration=kwargs['duration'],
            effect=effect)


if __name__ == "__main__":
    main()
