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
import time
import stat
import platform
import hashlib
import win32com.client
import mediatools.utilities as util


class File:
    '''File abstraction'''

    def __init__(self, filename):
        self.filename = filename
        self.size = None
        self.stats = None
        self.hash = None
        self.algo = None
        self.created = None
        self.modified = None

    def stat(self):
        try:
            self.stats = os.stat(self.filename)
            self.modified = time.localtime(self.stats[stat.ST_MTIME])
            self.created = time.localtime(self.stats[stat.ST_CTIME])
            self.size = self.stats[stat.ST_SIZE]
        except FileNotFoundError:
            return None

    def is_shortcut(self):
        if platform.system() != 'Windows':
            return False
        f = self.filename.lower()
        return f.endswith('.lnk') or f.endswith('.url')

    def is_link(self):
        if platform.system() == 'Windows':
            return self.filename.lower().endswith('.lnk')
        else:
            return os.path.islink()

    def read_link(self):
        if not is_link(self.filename):
            return None
        util.logger.info("Checking symlink %s", self.filename)
        if platform.system() == 'Windows':
            shell = win32com.client.Dispatch("WScript.Shell")
            return shell.CreateShortCut(self.filename).Targetpath
        else:
            return os.path.readlink()

    def create_link(self, link, dir=None, icon=None):
        if platform.system() == 'Windows':
            shell = win32com.client.Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(link)
            shortcut.Targetpath = self.filename
            if dir is not None:
                shortcut.WorkingDirectory = dir
            if icon is not None:
                shortcut.IconLocation = icon
            shortcut.save()
        else:
            os.symlink(self.filename, link)

    def extension(self):
        return self.filename.split('.').pop()

    def basename(self, ext=None):
        f = self.filename.split(os.sep).pop()
        if ext is None:
            return f
        else:
            return '.'.join(f.split('.')[0:-1])

    def get_hash(self, algo='md5'):
        if self.hash is not None and self.algo is not None and self.algo == algo:
            return self.hash
        BLOCK_SIZE = 65536  # The size of each read from the file
        try:
            file_hash = hashlib.md5()
            with open(self.filename, 'rb') as f:
                fb = f.read(BLOCK_SIZE)
                while len(fb) > 0:
                    file_hash.update(fb)
                    fb = f.read(BLOCK_SIZE)
            self.hash = file_hash.hexdigest()  # Get the hexadecimal digest of the hash
            self.algo = algo
            return self.hash
        except FileNotFoundError:
            return None

# ------------------------------------------------------------------------------


def extension(f):
    return File(f).extension()


def basename(f, ext=None):
    return File(f).extension()


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
