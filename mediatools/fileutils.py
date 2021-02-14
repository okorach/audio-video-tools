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
import platform
import hashlib
import win32com.client
import mediatools.utilities as util


def get_hash(file, algo='md5'):
    BLOCK_SIZE = 65536  # The size of each read from the file

    try:
        file_hash = hashlib.md5()
        with open(file, 'rb') as f:
            fb = f.read(BLOCK_SIZE)
            while len(fb) > 0:
                file_hash.update(fb)
                fb = f.read(BLOCK_SIZE)
        h = file_hash.hexdigest()
        util.logger.debug("Hash(%s) = %s", file, str(h))
        return h  # Get the hexadecimal digest of the hash
    except FileNotFoundError:
        return 0


def get_hash_list(filelist, algo='md5'):
    util.logger.info("Getting hashes of %d files", len(filelist))
    hashes = {}
    i = 0
    for f in filelist:
        try:
            _ = os.stat(f)
        except FileNotFoundError:
            continue
        h = get_hash(f, algo)
        if h in hashes:
            hashes[h].append(f)
        else:
            hashes[h] = [f]
        i += 1
        if (i % 100) == 0:
            util.logger.info("%d hashes computed", i)
    return hashes


def is_link(file):
    if platform.system() == 'Windows':
        return file.lower().endswith('.lnk')
    else:
        return os.path.islink()


def read_link(linkfile):
    if not is_link(linkfile):
        return None

    if platform.system() == 'Windows':
        shell = win32com.client.Dispatch("WScript.Shell")
        file = shell.CreateShortCut(linkfile).Targetpath
    else:
        file = os.path.readlink()
    util.logger.info("Follow link %s --> %s", linkfile, file)
    return file


def create_link(srcfile, linkfile):
    util.logger.info("Create link %s --> %s"), linkfile, srcfile
    if platform.system() == 'Windows':
        shell = win32com.client.Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(linkfile + '.lnk')
        shortcut.Targetpath = srcfile
        # shortcut.WorkingDirectory = wDir
        # shortcut.IconLocation = icon
        shortcut.save()
    else:
        os.symlink(srcfile, linkfile)
