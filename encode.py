#!/usr/local/bin/python3

import sys
import os
import re
from shutil import copyfile
import mediatools.videofile as video
import mediatools.audiofile as audio
import mediatools.imagefile as img
import mediatools.utilities as util
import mediatools.mediafile as media

def encode_file(args, options):
    '''Encodes a single file'''
    if util.is_audio_file(args.inputfile):
        file_object = audio.AudioFile(args.inputfile)
    elif util.is_image_file(args.inputfile):
        file_object = img.ImageFile(args.inputfile)
    else:
        file_object = video.VideoFile(args.inputfile)
    if args.vwidth is not None:
        specs = file_object.get_properties()
        w = int(specs['width'])
        h = int(specs['height'])
        new_w = int(args.vwidth)
        new_h = (int(h * new_w / w) // 8) * 8
        options['vsize'] = "%dx%d" % (new_w, new_h)
    if args.timeranges is None:
        file_object.encode(args.outputfile, args.profile, **options)
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
        outputfile = file_object.encode(target_file, args.profile, **options)
        util.logger.info("File %s generated", outputfile)
    if len(timeranges) > 1:
        # If more than 1 file generated, concatenate all generated files
        target_file = util.automatic_output_file_name(args.outputfile, args.inputfile, "combined", ext)
        video.concat(target_file, filelist)

def encode_dir(args, options):
    '''Encodes a whole directory'''
    targetdir = args.inputfile + '.' + args.profile
    util.logger.debug("%s ==> %s", args.inputfile, targetdir)
    os.makedirs(targetdir, exist_ok=True)

    ext = util.get_profile_extension(args.profile)
    filelist = util.filelist(args.inputfile)
    nbfiles = len(filelist)
    i = 0
    for fname in filelist:
        util.logger.info("%5d/%5d : %3d%% : %s", i, nbfiles, round(i * 100 / nbfiles), fname)
        targetfname = fname.replace(args.inputfile, targetdir, 1)
        if util.is_audio_file(fname) or util.is_video_file(fname):
            targetfname = util.strip_file_extension(targetfname) + r'.' + ext
            directory = os.path.dirname(targetfname)
            if not os.path.exists(directory):
                os.makedirs(directory)
            if util.is_audio_file(fname):
                o_file = audio.AudioFile(fname)
            else:
                o_file = video.VideoFile(fname)
            outputfile = o_file.encode(targetfname, args.profile, **options)
            util.logger.info("File %s generated", outputfile)
        else:
            # Simply copy non media files
            copyfile(fname, targetfname)
            util.logger.info("Skipping/Plain Copy file %s", fname)
        i = i + 1
    util.logger.info('%05d/%05d : 100%% : Job finished', nbfiles, nbfiles)

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
