#!/usr/local/bin/python3

'''
This scripts adds a shaky effect to an image
Effect can be horizontal or vertical
Arguments: -c <color> -r <ratio> -n <slices> -d <direction>
'''

import argparse
import mediatools.utilities as util
import mediatools.imagefile as image


def main():
    parser = util.parse_common_args('Image shake effect')
    parser.add_argument('-n', '--slices', required=False, default=10, help='Number of slices')
    parser.add_argument('-d', '--direction', required=False, default='vertical', help='Direction to slice')
    parser.add_argument('-c', '--color', required=False, default='black', help='Blinds color')
    parser.add_argument('-r', '--shake_ratio', required=False, default=3, help='Size of the shake')
    args = parser.parse_args()

    util.check_environment(vars(args))
    image.ImageFile(args.inputfile).shake(int(args.slices), float(args.shake_ratio), args.color, args.direction)


if __name__ == "__main__":
    main()
