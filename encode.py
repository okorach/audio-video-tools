#!python3

import sys
import os
import re
from shutil import copyfile
import mediatools.videofile as video
import mediatools.utilities as util
import mediatools.mediafile as media

def encode_file(args, options):
    if args.timeranges is None:
        video.encodeoo(args.inputfile, args.outputfile, args.profile, **options)
        return
    if args.outputfile is None:
        ext = util.get_profile_extension(args.profile)
    count = 0
    for video_range in re.split(',', args.timeranges):
        options['ss'], options['to'] = re.split('-', video_range)
        count += 1
        if args.outputfile is None:
            target_file = util.add_postfix(args.inputfile, str(count), ext)
        else:
            target_file = args.outputfile
        video.encodeoo(args.inputfile, target_file, args.profile, **options)

def encode_dir(args, options):
    targetdir = args.inputfile + '.' + args.profile
    util.debug(1, "%s ==> %s" % (args.inputfile, targetdir))
    try:
        os.mkdir(targetdir)
    except FileExistsError:
        pass
    ext = util.get_profile_extension(args.profile)
    filelist = util.filelist(args.inputfile)
    nbfiles = len(filelist)
    i = 0
    for fname in filelist:
        util.debug(0, "%5d/%5d : %3d%% : %s" % (i, nbfiles, round(i * 100 / nbfiles), fname))
        targetfname = fname.replace(args.inputfile, targetdir, 1)
        if util.is_audio_file(fname) or util.is_video_file(fname):
            targetfname = util.strip_file_extension(targetfname) + r'.' + ext
            directory = os.path.dirname(targetfname)
            if not os.path.exists(directory):
                os.makedirs(directory)
            video.encode(fname, targetfname, args.profile, **options)
        else:
            copyfile(fname, targetfname)
            util.debug(2, "Skipping/Plain Copy %s" % (fname))
        i = i + 1
    util.debug(0, '%05d/%05d : 100%% : Job finished' % (nbfiles, nbfiles))

parser = util.parse_common_args('Audio and Video file (re)encoder')
args = parser.parse_args()
util.set_debug_level(args.debug)
options = util.cleanup_options(vars(args))

if os.path.isdir(args.inputfile):
    encode_dir(args, options)
else:
    encode_file(args, options)
