#!/usr/local/bin/python3

import argparse
import mediatools.utilities as util
import mediatools.imagefile as image


def main():
    parser = util.parse_common_args('image2video')
    parser.add_argument('-z', '--zoom_level', required=False, default=1.3, help='Number of blinds')
    kwargs = vars(parser.parse_args())

    util.check_environment(kwargs)
    inputfile = kwargs.pop('inputfile')
    image.ImageFile(inputfile).zoom_in(final_zoom=kwargs['zoom_level'], resolution=kwargs['framesize'])


if __name__ == "__main__":
    main()
