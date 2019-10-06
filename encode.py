#!/usr/local/bin/python3

import sys
import os
import re
from shutil import copyfile
import mediatools.videofile as video
import mediatools.utilities as util
import mediatools.mediafile as media

def encode_file(args, options):
    if util.is_video_file(args.inputfile) and args.vwidth is not None:
        file_object = video.VideoFile(args.inputfile)
        specs = file_object.get_properties()
        w = int(specs['width'])
        h = int(specs['height'])
        new_w = int(args.vwidth)
        new_h = (int(h * new_w / w) // 8) * 8
        options['vsize'] = "%dx%d" % (new_w, new_h)
    if args.timeranges is None:
        video.encodeoo(args.inputfile, args.outputfile, args.profile, **options)
        return
    if args.outputfile is None:
        ext = util.get_profile_extension(args.profile)
    count = 0
    filelist = []
    timeranges = re.split(',', args.timeranges)
    for video_range in timeranges:
        options['start'], options['stop'] = re.split('-', video_range)
        count += 1
        target_file = util.automatic_output_file_name(args.outputfile, args.inputfile, str(count), ext)
        filelist.append(target_file)
        video.encodeoo(args.inputfile, target_file, args.profile, **options)
    if len(timeranges) > 1:
        target_file = util.automatic_output_file_name(args.outputfile, args.inputfile, "combined", ext)
        video.concat(target_file, filelist)

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
parser = video.add_video_args(parser)

myargs = parser.parse_args()
myoptions = vars(myargs)
util.check_environment(myoptions)
myoptions = util.cleanup_options(myoptions)

if os.path.isdir(myargs.inputfile):
    encode_dir(myargs, myoptions)
else:
    encode_file(myargs, myoptions)
