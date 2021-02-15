#!python3
#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import os
import re
import time
import stat
import platform
import hashlib
if platform.system() == 'Windows':
    import win32com.client
import mediatools.utilities as util


class FileType:
    AUDIO_FILE = 'audio'
    VIDEO_FILE = 'video'
    IMAGE_FILE = 'image'
    UNKNOWN_FILE = 'unknown'
    FILE_EXTENSIONS = {
        AUDIO_FILE: r'\.(mp3|ogg|aac|ac3|m4a|ape|flac)$',
        VIDEO_FILE: r'\.(avi|wmv|mp4|3gp|mpg|mpeg|mkv|ts|mts|m2ts|mov)$',
        IMAGE_FILE: r'\.(jpg|jpeg|png|gif|svg|raw)$'
    }


class File:
    '''File abstraction'''

    def __init__(self, filename):
        self.filename = filename
        self.size = None
        self.created = None
        self.modified = None
        self.stat = None
        self._hash = None
        self.algo = None

    def probe(self, force=False):
        if self.stat is not None and not force:
            return True
        try:
            self.stat = os.stat(self.filename)
            self.modified = time.localtime(self.stat[stat.ST_MTIME])
            self.created = time.localtime(self.stat[stat.ST_CTIME])
            self.size = self.stat[stat.ST_SIZE]
            return True
        except FileNotFoundError:
            return False

    def is_shortcut(self):
        if platform.system() != 'Windows':
            return False
        f = self.filename.lower()
        return f.endswith('.lnk') or f.endswith('.url')

    def is_link(self):
        if platform.system() == 'Windows':
            return self.filename.lower().endswith('.lnk')
        else:
            return os.path.islink(self.filename)

    def read_link(self):
        if not is_link(self.filename):
            return None
        util.logger.info("Checking symlink %s", self.filename)
        if platform.system() == 'Windows':
            shell = win32com.client.Dispatch("WScript.Shell")
            return shell.CreateShortCut(self.filename).Targetpath
        else:
            return os.path.readlink(self.filename)

    def create_link(self, link, dir=None, icon=None):
        if platform.system() == 'Windows':
            shell = win32com.client.Dispatch('WScript.Shell')
            if not link.endswith('.lnk'):
                link += '.lnk'
            util.logger.debug("Create shortcut: %s --> %s", link, self.filename)
            shortcut = shell.CreateShortCut(link)
            shortcut.Targetpath = self.filename
            if dir is not None:
                shortcut.WorkingDirectory = dir
            if icon is not None:
                shortcut.IconLocation = icon
            shortcut.save()
        else:
            util.logger.debug("Create symlink: %s --> %s", link, self.filename)
            os.symlink(self.filename, link)

    def extension(self):
        return self.filename.split('.').pop()

    def basename(self, ext=None):
        f = self.filename.split(os.sep).pop()
        if ext is None:
            return f
        else:
            return '.'.join(f.split('.')[0:-1])

    def dirname(self):
        return os.sep.join(self.filename.split(os.sep)[0:-1])

    def hash(self, algo='md5', force=False):
        if self._hash is not None and self.algo is not None and self.algo == algo and not force:
            return self._hash
        BLOCK_SIZE = 65536  # The size of each read from the file
        try:
            file_hash = hashlib.md5()
            with open(self.filename, 'rb') as f:
                fb = f.read(BLOCK_SIZE)
                while len(fb) > 0:
                    file_hash.update(fb)
                    fb = f.read(BLOCK_SIZE)
            self._hash = file_hash.hexdigest()  # Get the hexadecimal digest of the hash
            self.algo = algo
            return self._hash
        except FileNotFoundError:
            return None

# ------------------------------------------------------------------------------


def extension(f):
    return File(f).extension()


def basename(f, ext=None):
    return File(f).basename(ext)


def dirname(f):
    return File(f).dirname()


def is_link(f):
    return File(f).is_link()


def is_shortcut(f):
    return File(f).is_shortcut()


def read_link(f):
    return File(f).read_link()


def create_link(f, link):
    return File(f).create_link(link)


def get_hash_list(filelist, algo='md5'):
    util.logger.info("Getting hashes of %d files", len(filelist))
    hashes = {}
    i = 0
    for f in filelist:
        h = File(f).hash(algo)
        if h is None:
            continue
        if h in hashes:
            hashes[h].append(f)
        else:
            hashes[h] = [f]
        i += 1
        if (i % 100) == 0:
            util.logger.info("%d hashes computed", i)
    return hashes


def strip_file_extension(filename):
    """Removes the file extension and returns the string"""
    return '.'.join(filename.split('.')[:-1])


def __match_extension__(file, regex):
    """Returns boolean, whether the file has a extension that matches the regex (case insensitive)"""
    ext = '.' + extension(file)
    p = re.compile(regex, re.IGNORECASE)
    return not re.search(p, ext) is None


def dir_list(root_dir, recurse=False, file_type=None):
    """Returns and array of all files under a given root directory
    going down into sub directories"""
    util.logger.info("Searching files in %s (recurse=%s)", root_dir, str(recurse))
    files = []
    # 3 params are r=root, _=directories, f = files
    for r, _, f in os.walk(root_dir):
        for file in f:
            if os.path.isdir(file) and recurse:
                files.append(dir_list(file, recurse=recurse, file_type=file_type))
            elif __is_type_file(os.path.join(r, file), file_type):
                files.append(os.path.join(r, file))
    util.logger.info("Found %d files in %s", len(files), root_dir)
    return files


def file_list(*args, file_type=None, recurse=False):
    util.logger.debug("Searching files in %s", str(args))
    files = []
    for arg in args:
        util.logger.debug("Check file %s", str(arg))
        if os.path.isdir(arg):
            files.extend(dir_list(arg, file_type=file_type, recurse=recurse))
        elif file_type is None or __is_type_file(arg, file_type):
            files.append(arg)
    return files


def __is_type_file(file, type_of_media):
    return type_of_media is None or (
        os.path.isfile(file) and __match_extension__(file, FileType.FILE_EXTENSIONS[type_of_media]))


def is_audio_file(file):
    return __is_type_file(file, FileType.AUDIO_FILE)


def is_video_file(file):
    return __is_type_file(file, FileType.VIDEO_FILE)


def is_image_file(file):
    return __is_type_file(file, FileType.IMAGE_FILE)


def is_media_file(file):
    """Returns whether the file has an extension corresponding to media (audio/video/image) files"""
    return is_audio_file(file) or is_image_file(file) or is_video_file(file)


def get_type(file):
    if is_audio_file(file):
        t = FileType.AUDIO_FILE
    elif is_video_file(file):
        t = FileType.VIDEO_FILE
    elif is_image_file(file):
        t = FileType.IMAGE_FILE
    else:
        t = FileType.UNKNOWN_FILE
    util.logger.debug("Filetype of %s is %s", file, t)
    return t
