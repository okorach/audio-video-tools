#!/Library/Frameworks/Python.framework/Versions/3.6/bin/python3

import sys
import os
import re
import mediatools.videofile as video
import mediatools.utilities as util
import mediatools.mediafile as media

parser = util.parse_common_args('Audio and Video file (re)encoder')
args = parser.parse_args()
util.set_debug_level(int(args.debug))
options = util.cleanup_options(vars(args))

if os.path.isdir(args.inputfile):
    targetdir = args.inputfile + '.' + args.profile
    try:
        os.mkdir(targetdir)
    except FileExistsError:
        pass
    ext = util.get_profile_extension(args.profile)
    util.debug(1, "%s ==> %s" % (args.inputfile, targetdir))
    filelist = util.filelist(args.inputfile)
    nbfiles = len(filelist)
    i = 0
    for fname in filelist:
        source_extension =  util.get_file_extension(fname)
        print ("%5d/%5d : %3d%% : " % (i, nbfiles, round(i * 100 / nbfiles)))
        if util.is_audio_file(fname) or util.is_video_file(fname):
            targetfname = fname.replace(args.inputfile, targetdir, 1)
            targetfname = util.strip_file_extension(targetfname) + r'.' + ext
            directory = os.path.dirname(targetfname)
            if not os.path.exists(directory):
                os.makedirs(directory)
            video.encode(fname, targetfname, args.profile, **options)
        else:
            from shutil import copyfile
            targetfname = fname.replace(args.inputfile, targetdir, 1)
            copyfile(fname, targetfname)
            print("Skipping/Plain Copy %s" % (fname))
        i = i + 1
    print ('100%: Job finished')
else:
    if args.timeranges is None:
        video.encodeoo(args.inputfile, args.outputfile, args.profile, **options)
    else:
        if args.outputfile is None:
            ext = util.get_profile_extension(args.profile)
        count = 0
        for video_range in re.split(',', args.timeranges):
            start, stop = re.split('-', video_range)
            options['ss'] = start
            options['to'] = stop
            count = count + 1
            if args.outputfile is None:
                target_file = util.add_postfix(args.inputfile, str(count), ext)
            else:
                target_file = args.outputfile
            video.encodeoo(args.inputfile, target_file, args.profile, **options)
