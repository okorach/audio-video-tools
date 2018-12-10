#!/usr/local/bin/python3

import videotools.videofile
import sys
import os
import re

parser = videotools.videofile.parse_common_args('Audio and Video file (re)encoder')
args = parser.parse_args()
if args.debug:
    videotools.filetools.set_debug_level(int(args.debug))
options = videotools.videofile.cleanup_options(vars(args))

if (os.path.isdir(args.inputfile)):
    targetdir = args.inputfile + '.' + args.profile
    try:
        os.mkdir(targetdir)
    except FileExistsError:
        pass
    ext = videotools.videofile.get_profile_extension(args.profile)
    print ("%s ==> %s" % (args.inputfile, targetdir))
    filelist = videotools.filetools.filelist(args.inputfile)
    nbfiles = len(filelist)
    i = 0
    for fname in filelist:
        source_extension =  videotools.filetools.get_file_extension(fname)
        print ("%5d/%5d : %3d%% : " % (i, nbfiles, round(i * 100 / nbfiles)))
        if videotools.filetools.is_audio_file(fname) or videotools.filetools.is_video_file(fname):
            targetfname = fname.replace(args.inputfile, targetdir, 1)
            targetfname = videotools.filetools.strip_file_extension(targetfname) + r'.' + ext
            directory = os.path.dirname(targetfname)
            if not os.path.exists(directory):
                os.makedirs(directory)
            videotools.videofile.encode(fname, targetfname, args.profile, **options)
            #videofile.encode(fname, targetfname, args.profile)
        else:
            from shutil import copyfile
            targetfname = fname.replace(args.inputfile, targetdir, 1)
            copyfile(fname, targetfname)
            print("Skipping/Plain Copy %s" % (fname))
        i = i + 1
    print ('100%: Job finished')
else:
    videotools.videofile.encode(args.inputfile, None, args.profile, **options)
