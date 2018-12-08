#!python3

import videotools.videofile, videotools.filetools
import sys
import os
import re

def parse_args():
    parser = argparse.ArgumentParser(
            description='Python wrapper for ffmpeg.')
    parser.add_argument('-i', '--inputfile', required=True,
                           help='Input File or Directory to encode'
                        )
    parser.add_argument('-p', '--profile', required=True,
                           help='Profile to use for encoding'
                        )
    args = parser.parse_args()

    return args

try:
    import argparse
except ImportError:
    if sys.version_info < (2, 7, 0):
        print("Error:")
        print("You are running an old version of python. Two options to fix the problem")
        print("  Option 1: Upgrade to python version >= 2.7")
        print("  Option 2: Install argparse library for the current python version")
        print("            See: https://pypi.python.org/pypi/argparse")

args = parse_args()

if (os.path.isdir(args.inputfile)):
    targetdir = args.inputfile + '.' + args.profile
    try:
        os.mkdir(targetdir)
    except FileExistsError:
        pass
    ext = videotools.filetools.get_file_extension(args.profile)
    print ("%s ==> %s" % (args.inputfile, targetdir))
    filelist = videotools.filetools.filelist(args.inputfile)
    nbfiles = len(filelist)
    i = 0
    for fname in filelist:
        source_extension =  videotools.filetools.get_file_extension(fname)
        print ("%5d/%5d : %3d%% : " % (i, nbfiles, round(i * 100 / nbfiles)))
        if re.match(r'(mp3|ogg|aac|ac3|m4a|ape|avi|wmv|mp4|3gp|mpg|mpeg|mkv|ts|mts|m2ts)', source_extension):
            targetfname = fname.replace(args.inputfile, targetdir, 1)
            targetfname = videotools.filetools.strip_file_extension(targetfname) + r'.' + ext

            directory = os.path.dirname(targetfname)
            if not os.path.exists(directory):
                os.makedirs(directory)
            videotools.videofile.encode(fname, targetfname, args.profile)
            #videofile.encode(fname, targetfname, args.profile)
        else:
            from shutil import copyfile
            targetfname = fname.replace(args.inputfile, targetdir, 1)
            copyfile(fname, targetfname)
            print("Skipping/Plain Copy %s" % (fname))
        i = i + 1
    print ('100%: Job finished')
else:
    videotools.videofile.encode(args.inputfile, None, args.profile)
