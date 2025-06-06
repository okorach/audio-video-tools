#!python3
#
# media-tools
# Copyright (C) 2019-2024 Olivier Korach
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
from mediatools import log

if platform.system() == "Windows":
    import win32com.client


class FileType:
    AUDIO_FILE = "audio"
    VIDEO_FILE = "video"
    IMAGE_FILE = "image"
    UNKNOWN_FILE = "unknown"
    FILE_EXTENSIONS = {
        AUDIO_FILE: ("mp3", "ogg", "aac", "ac3", "m4a", "ape", "flac", "opus"),
        VIDEO_FILE: ("avi", "wmv", "mp4", "3gp", "mpg", "mpeg", "mkv", "ts", "mts", "m2ts", "mov"),
        IMAGE_FILE: ("jpg", "jpeg", "png", "gif", "svg", "raw"),
    }


MEDIA_FILE_EXTENSIONS = (
    FileType.FILE_EXTENSIONS[FileType.AUDIO_FILE] + FileType.FILE_EXTENSIONS[FileType.VIDEO_FILE] + FileType.FILE_EXTENSIONS[FileType.IMAGE_FILE]
)

IMAGE_AND_VIDEO_EXTENSIONS = FileType.FILE_EXTENSIONS[FileType.VIDEO_FILE] + FileType.FILE_EXTENSIONS[FileType.IMAGE_FILE]


class File:
    """File abstraction"""

    def __init__(self, filename: str) -> None:
        self.filename = os.path.abspath(filename)
        self._size = None
        self.created = None
        self.modified = None
        self._stat = None
        self._hash = None
        self.algo = None

    def stat(self, force: bool = False) -> bool:
        if self._stat is not None and not force:
            return True
        try:
            self._stat = os.stat(self.filename)
            self.modified = time.localtime(self._stat[stat.ST_MTIME])
            self.created = time.localtime(self._stat[stat.ST_CTIME])
            self._size = self._stat[stat.ST_SIZE]
            return True
        except FileNotFoundError:
            return False

    def modification_date(self, force: bool = False):
        if self.modified is None or force:
            self.stat()
        return self.modified

    def creation_date(self, force: bool = False):
        if self.created is None or force:
            self.stat()
        return self.created

    def size(self, force: bool = False) -> int:
        if self._size is None or force:
            self.stat()
        return self._size

    def is_shortcut(self):
        if platform.system() != "Windows":
            return False
        f = self.filename.lower()
        return f.endswith(".lnk") or f.endswith(".url")

    def is_link(self):
        if platform.system() == "Windows":
            return self.filename.lower().endswith(".lnk")
        else:
            return os.path.islink(self.filename)

    def read_link(self):
        if not is_link(self.filename):
            return None
        log.logger.info("Checking symlink %s", self.filename)
        if platform.system() == "Windows":
            shell = win32com.client.Dispatch("WScript.Shell")
            return shell.CreateShortCut(self.filename).Targetpath
        else:
            return os.readlink(self.filename)

    def create_link(self, link: str, dir: str = None, icon: str = None) -> str:
        if platform.system() == "Windows":
            shell = win32com.client.Dispatch("WScript.Shell")
            if not link.endswith(".lnk"):
                link += ".lnk"
            log.logger.debug("Create shortcut: %s --> %s", link, self.filename)
            shortcut = shell.CreateShortCut(link)
            shortcut.Targetpath = self.filename
            if dir is not None:
                shortcut.WorkingDirectory = dir
            if icon is not None:
                shortcut.IconLocation = icon
            shortcut.save()
            return link
        else:
            log.logger.debug("Create symlink: %s --> %s", link, self.filename)
            os.symlink(self.filename, link)
            return link

    def extension(self) -> str:
        return self.filename.split(".")[-1]

    def basename(self, strip_dir: bool = True, strip_ext: bool = True) -> str:
        f = self.filename if not strip_dir else self.filename.split(os.sep)[-1]
        return ".".join(f.split(".")[0:-1]) if strip_ext else f

    def dirname(self) -> str:
        return os.sep.join(os.path.abspath(self.filename).split(os.sep)[0:-1])

    def strip_extension(self):
        return self.basename(strip_dir=False, strip_ext=True)

    def hash(self, algo="md5", force=False):
        if self._hash is not None and self.algo is not None and self.algo == algo and not force:
            return self._hash
        BLOCK_SIZE = 65536  # The size of each read from the file
        try:
            file_hash = hashlib.md5()
            with open(self.filename, "rb") as f:
                fb = f.read(BLOCK_SIZE)
                while len(fb) > 0:
                    file_hash.update(fb)
                    fb = f.read(BLOCK_SIZE)
            self._hash = file_hash.hexdigest()  # Get the hexadecimal digest of the hash
            self.algo = algo
            return self._hash
        except FileNotFoundError:
            return None

    def rename(self, new_name: str, overwrite: bool = False) -> str:
        if os.path.isfile(new_name):
            if overwrite:
                os.remove(new_name)
            else:
                file_split = new_name.split(".")
                base = ".".join(file_split[0:-1])
                ext = file_split[-1]
                seq = 0
                while os.path.isfile(f"{base}.{seq:03}.{ext}"):
                    seq += 1
                os.rename(new_name, f"{base}.bak.{seq:03}.{ext}")
        os.rename(self.filename, new_name)
        return new_name

    def add_postfix(self, postfix: str):
        """Adds a postfix to a file before the file extension"""
        return f"{self.strip_extension()}.{postfix}.{self.extension()}"


# ------------------------------------------------------------------------------


def rename(old: str, new: str, overwrite: bool = False) -> str:
    return File(old).rename(new, overwrite)


def extension(f: str) -> str:
    return File(f).extension()


def basename(f: str, strip_dir: bool = True, strip_ext: bool = True) -> str:
    return File(f).basename(strip_dir=strip_dir, strip_ext=strip_ext)


def strip_extension(f: str):
    return File(f).strip_extension()


def dirname(f: str) -> str:
    return File(f).dirname()


def add_postfix(file: str, postfix: str):
    """Adds a postfix to a file before the file extension"""
    return File(file).add_postfix(postfix)


def is_link(f) -> bool:
    return File(f).is_link()


def is_shortcut(f) -> bool:
    return File(f).is_shortcut()


def read_link(f):
    return File(f).read_link()


def create_link(f: str, link: str) -> str:
    return File(f).create_link(link)


def get_hash_list(filelist, algo: str = "md5") -> dict[str, list[str]]:
    log.logger.info("Getting hashes of %d files", len(filelist))
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
            log.logger.info("%d hashes computed", i)
    return hashes


def strip_file_extension(filename: str) -> str:
    """Removes the file extension and returns the string"""
    return ".".join(filename.split(".")[:-1])


def __match_extension(file: str, extension_list: list[str]) -> bool:
    """Returns boolean, whether the file has a extension that is in the list"""
    return extension(file).lower() in extension_list


def dir_list(root_dir: str, recurse: bool = False, file_type: str = None):
    """Returns and array of all files under a given root directory
    going down into sub directories"""
    log.logger.info("Searching files in %s (recurse=%s)", root_dir, str(recurse))
    files = []
    # 3 params are r=root, _=directories, f = files
    for r, _, f in os.walk(root_dir):
        for file in f:
            if os.path.isdir(file) and recurse:
                files.append(dir_list(file, recurse=recurse, file_type=file_type))
            elif __is_type_file(os.path.join(r, file), file_type):
                files.append(os.path.join(r, file))
    log.logger.info("Found %d files in %s", len(files), root_dir)
    return files


def file_list(*args, file_type: str = None, recurse: bool = False):
    log.logger.debug("Searching files in %s", str(args))
    files = []
    for arg in args:
        log.logger.debug("Check file %s", str(arg))
        if os.path.isdir(arg):
            files.extend(dir_list(arg, file_type=file_type, recurse=recurse))
        elif file_type is None or __is_type_file(arg, file_type):
            files.append(arg)
    return files


def __is_type_file(file, type_of_media: str) -> bool:
    return type_of_media is None or (
        (os.path.isfile(file) or file[0:2] == "\\\\") and __match_extension(file, FileType.FILE_EXTENSIONS[type_of_media])
    )


def is_audio_file(file: str) -> bool:
    return __is_type_file(file, FileType.AUDIO_FILE)


def is_video_file(file: str) -> bool:
    return __is_type_file(file, FileType.VIDEO_FILE)


def is_image_file(file: str) -> bool:
    return __is_type_file(file, FileType.IMAGE_FILE)


def is_media_file(file: str) -> bool:
    """Returns whether the file has an extension corresponding to media (audio/video/image) files"""
    return is_audio_file(file) or is_image_file(file) or is_video_file(file)


def get_type(file: str) -> str:
    if is_audio_file(file):
        t = FileType.AUDIO_FILE
    elif is_video_file(file):
        t = FileType.VIDEO_FILE
    elif is_image_file(file):
        t = FileType.IMAGE_FILE
    else:
        t = FileType.UNKNOWN_FILE
    log.logger.debug("Filetype of %s is %s", file, t)
    return t


def random_name(original_file: str, pattern: str, file_ext: str = None) -> str:
    file_ext = "" if file_ext is None else f".{file_ext}"
    return f"{strip_extension(original_file)}.{pattern}.{os.getpid()}{file_ext}"
