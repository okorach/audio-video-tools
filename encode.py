#!/usr/local/bin/python3

import mediatools.videofile
import sys
import os
import re

parser = mediatools.videofile.parse_common_args('Audio and Video file (re)encoder')
args = parser.parse_args()
if args.debug:
    mediatools.utilities.set_debug_level(int(args.debug))
options = mediatools.videofile.cleanup_options(vars(args))

if (os.path.isdir(args.inputfile)):
    targetdir = args.inputfile + '.' + args.profile
    try:
        os.mkdir(targetdir)
    except FileExistsError:
        pass
    ext = mediatools.videofile.get_profile_extension(args.profile)
    print ("%s ==> %s" % (args.inputfile, targetdir))
    filelist = mediatools.utilities.filelist(args.inputfile)
    nbfiles = len(filelist)
    i = 0
    for fname in filelist:
        source_extension =  mediatools.utilities.get_file_extension(fname)
        print ("%5d/%5d : %3d%% : " % (i, nbfiles, round(i * 100 / nbfiles)))
        if mediatools.utilities.is_audio_file(fname) or mediatools.utilities.is_video_file(fname):
            targetfname = fname.replace(args.inputfile, targetdir, 1)
            targetfname = mediatools.utilities.strip_file_extension(targetfname) + r'.' + ext
            directory = os.path.dirname(targetfname)
            if not os.path.exists(directory):
                os.makedirs(directory)
            mediatools.videofile.encode(fname, targetfname, args.profile, **options)
            #videofile.encode(fname, targetfname, args.profile)
        else:
            from shutil import copyfile
            targetfname = fname.replace(args.inputfile, targetdir, 1)
            copyfile(fname, targetfname)
            print("Skipping/Plain Copy %s" % (fname))
        i = i + 1
    print ('100%: Job finished')
else:
    if args.ranges is None:
        mediatools.videofile.encode(args.inputfile, args.outputfile, args.profile, **options)
    else:
        if args.outputfile is None:
            ext = mediatools.videofile.get_profile_extension(args.profile)
        count = 0
        for range in re.split(',', args.ranges):
            start, stop = re.split('-', range)
            options['ss'] = start
            options['to'] = stop
            count = count + 1
            if args.outputfile is None:
                target_file = mediatools.utilities.add_postfix(args.inputfile, str(count), ext)
            else:
                target_file = args.outputfile
            mediatools.videofile.encode(args.inputfile, target_file, args.profile, **options)



