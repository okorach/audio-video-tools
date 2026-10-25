#
# media-tools
# Copyright (C) 2019-2026 Olivier Korach
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

"""File abstraction: names, dates, hashes, links, types of files and lists of files"""

import os
import time
import stat
import platform
import hashlib
from typing import ClassVar
from mediatools import log

if platform.system() == "Windows":
    import win32com.client


class FileType:
    """Types of files (audio, video, image) and their extensions"""

    AUDIO_FILE: str = "audio"
    VIDEO_FILE: str = "video"
    IMAGE_FILE: str = "image"
    UNKNOWN_FILE: str = "unknown"
    FILE_EXTENSIONS: ClassVar[dict[str, tuple[str, ...]]] = {
        AUDIO_FILE: ("mp3", "ogg", "aac", "ac3", "m4a", "ape", "flac", "opus"),
        VIDEO_FILE: ("avi", "wmv", "mp4", "3gp", "mpg", "mpeg", "mkv", "ts", "mts", "m2ts", "mov"),
        IMAGE_FILE: ("jpg", "jpeg", "png", "gif", "svg", "raw"),
    }


MEDIA_FILE_EXTENSIONS: tuple[str, ...] = (
    FileType.FILE_EXTENSIONS[FileType.AUDIO_FILE] + FileType.FILE_EXTENSIONS[FileType.VIDEO_FILE] + FileType.FILE_EXTENSIONS[FileType.IMAGE_FILE]
)

IMAGE_AND_VIDEO_EXTENSIONS: tuple[str, ...] = FileType.FILE_EXTENSIONS[FileType.VIDEO_FILE] + FileType.FILE_EXTENSIONS[FileType.IMAGE_FILE]


class File:
    """File abstraction"""

    def __init__(self, filename: str) -> None:
        """Creates a file object from a file name (the name is converted to an absolute path)"""
        self.filename: str = os.path.abspath(filename)
        self._size: int | None = None
        self.created: time.struct_time | None = None
        self.modified: time.struct_time | None = None
        self._stat: os.stat_result | None = None
        self._hash: str | None = None
        self.algo: str | None = None

    def stat(self, force: bool = False) -> bool:
        """Reads the status of the file (size and dates), unless it was already read and force is not set. Returns False if the file can't be read"""
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

    def modification_date(self, force: bool = False) -> time.struct_time | None:
        """Returns the date of the last modification of the file"""
        if self.modified is None or force:
            self.stat()
        return self.modified

    def creation_date(self, force: bool = False) -> time.struct_time | None:
        """Returns the creation date of the file"""
        if self.created is None or force:
            self.stat()
        return self.created

    def size(self, force: bool = False) -> int:
        """Returns the size of the file in bytes"""
        if self._size is None or force:
            self.stat()
        return self._size

    def is_shortcut(self) -> bool:
        """Returns True if the file is a Windows shortcut (.lnk or .url), always False on the other platforms"""
        if platform.system() != "Windows":
            return False
        f = self.filename.lower()
        return f.endswith((".lnk", ".url"))

    def is_link(self) -> bool:
        """Returns True if the file is a link: a Windows shortcut on Windows, a symbolic link otherwise"""
        if platform.system() == "Windows":
            return self.filename.lower().endswith(".lnk")
        return os.path.islink(self.filename)

    def read_link(self) -> str | None:
        """Returns the target of a link (shortcut or symbolic link), None if the file is not a link"""
        if not is_link(self.filename):
            return None
        log.logger.info("Checking symlink %s", self.filename)
        if platform.system() == "Windows":
            shell = win32com.client.Dispatch("WScript.Shell")
            return shell.CreateShortCut(self.filename).Targetpath
        return os.readlink(self.filename)

    def create_link(self, link: str, directory: str | None = None, icon: str | None = None) -> str:
        """Creates a link (a shortcut on Windows, a symbolic link otherwise) to the file and returns its name"""
        if platform.system() == "Windows":
            shell = win32com.client.Dispatch("WScript.Shell")
            if not link.endswith(".lnk"):
                link += ".lnk"
            log.logger.debug("Create shortcut: %s --> %s", link, self.filename)
            shortcut = shell.CreateShortCut(link)
            shortcut.Targetpath = self.filename
            if directory is not None:
                shortcut.WorkingDirectory = directory
            if icon is not None:
                shortcut.IconLocation = icon
            shortcut.save()
            return link
        log.logger.debug("Create symlink: %s --> %s", link, self.filename)
        os.symlink(self.filename, link)
        return link

    def extension(self) -> str:
        """Returns the extension of the file, without the dot"""
        return self.filename.split(".")[-1]

    def basename(self, strip_dir: bool = True, strip_ext: bool = True) -> str:
        """Returns the name of the file, optionally without its directory and without its extension"""
        f = self.filename if not strip_dir else self.filename.split(os.sep)[-1]
        return ".".join(f.split(".")[0:-1]) if strip_ext else f

    def dirname(self) -> str:
        """Returns the directory of the file"""
        return os.sep.join(os.path.abspath(self.filename).split(os.sep)[0:-1])

    def strip_extension(self) -> str:
        """Returns the full path of the file without its extension"""
        return self.basename(strip_dir=False, strip_ext=True)

    def hash(self, algo: str = "md5", force: bool = False) -> str | None:
        """Returns the md5 hash of the content of the file (kept for the next calls), None if the file does not exist"""
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
        """Renames the file. If new_name exists, it is overwritten when overwrite is set, or renamed with a .bak postfix. Returns the new name"""
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

    def add_postfix(self, postfix: str) -> str:
        """Adds a postfix to a file before the file extension"""
        return f"{self.strip_extension()}.{postfix}.{self.extension()}"


# ------------------------------------------------------------------------------


def rename(old: str, new: str, overwrite: bool = False) -> str:
    """Renames a file and returns its new name, see File.rename()"""
    return File(old).rename(new, overwrite)


def extension(f: str) -> str:
    """Returns the extension of a file, without the dot"""
    return File(f).extension()


def basename(f: str, strip_dir: bool = True, strip_ext: bool = True) -> str:
    """Returns the name of a file, optionally without its directory and without its extension"""
    return File(f).basename(strip_dir=strip_dir, strip_ext=strip_ext)


def strip_extension(f: str) -> str:
    """Returns the full path of a file without its extension"""
    return File(f).strip_extension()


def dirname(f: str) -> str:
    """Returns the directory of a file"""
    return File(f).dirname()


def add_postfix(file: str, postfix: str) -> str:
    """Adds a postfix to a file before the file extension"""
    return File(file).add_postfix(postfix)


def is_link(f: str) -> bool:
    """Returns True if a file is a link (a shortcut on Windows, a symbolic link otherwise)"""
    return File(f).is_link()


def is_shortcut(f: str) -> bool:
    """Returns True if a file is a Windows shortcut, always False on the other platforms"""
    return File(f).is_shortcut()


def read_link(f: str) -> str | None:
    """Returns the target of a link, None if the file is not a link"""
    return File(f).read_link()


def create_link(f: str, link: str) -> str:
    """Creates a link to a file and returns its name"""
    return File(f).create_link(link)


def get_hash_list(filelist: list[str], algo: str = "md5") -> dict[str, list[str]]:
    """Returns the files grouped by hash: a dictionary of the hash (md5 by default) to the list of the files that have this hash"""
    log.logger.info("Getting hashes of %d files", len(filelist))
    hashes: dict[str, list[str]] = {}
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


def __match_extension(file: str, extension_list: tuple[str, ...] | list[str]) -> bool:
    """Returns boolean, whether the file has a extension that is in the list"""
    return extension(file).lower() in extension_list


def dir_list(root_dir: str, recurse: bool = False, file_type: str | None = None) -> list[str]:
    """Returns and array of all files under a given root directory
    going down into sub directories"""
    log.logger.info("Searching files in %s (recurse=%s)", root_dir, str(recurse))
    files: list[str] = []
    # 3 params are r=root, _=directories, f = files
    for r, _, f in os.walk(root_dir):
        for file in f:
            if os.path.isdir(file) and recurse:
                files.append(dir_list(file, recurse=recurse, file_type=file_type))
            elif __is_type_file(os.path.join(r, file), file_type):
                files.append(os.path.join(r, file))
    log.logger.info("Found %d files in %s", len(files), root_dir)
    return files


def file_list(*args: str, file_type: str | None = None) -> list[str]:
    """Returns the list of the files given as arguments: files, or the files found in directories, optionally of a type, optionally recursively"""
    log.logger.debug("Searching files in %s", str(args))
    files: list[str] = []
    for arg in args:
        log.logger.debug("Check file %s", str(arg))
        if os.path.isdir(arg):
            files.extend(expand_inputs([arg], file_type))
        elif file_type is None or __is_type_file(arg, file_type):
            files.append(arg)
    return files


def expand_inputs(
    paths: list[str] | tuple[str, ...], file_type: str | tuple[str, ...] | list[str] | None = None, extensions: tuple[str, ...] | None = None
) -> list[str]:
    """Expands a list of files and directories into a list of files.
    - A file is kept as is (even if it doesn't exist or doesn't match file_type: the tool decides what to do with it)
    - A directory is replaced by all the files it contains, recursively, in alphabetical order of their paths (case insensitive).
      Only files matching file_type (a FileType, or a list of FileTypes) are taken, or any audio/video/image file if file_type is None.
      If extensions (lowercase, without the dot) is given, it replaces file_type, eg ("pdf",)
    The order of the arguments is preserved (a file given several times is returned several times, as concatenating a file with itself is legitimate)
    """
    if isinstance(file_type, str):
        file_type = (file_type,)
    if extensions is None:
        extensions = MEDIA_FILE_EXTENSIONS if file_type is None else tuple(e for t in file_type for e in FileType.FILE_EXTENSIONS[t])
    files: list[str] = []
    for path in paths:
        if os.path.isdir(path):
            found: list[str] = []
            for root, _, names in os.walk(path):
                found.extend(os.path.join(root, name) for name in names if __match_extension(name, extensions))
            found.sort(key=lambda f: [part.lower() for part in os.path.normpath(f).split(os.sep)])
            log.logger.info("Found %d files in directory %s", len(found), path)
            if not found:
                log.logger.warning("No matching file found in directory %s", path)
            files.extend(found)
        else:
            files.append(path)
    return files


def __is_type_file(file: str, type_of_media: str | None) -> bool:
    """Returns True if no type is requested, or if the file is an existing file with an extension of the requested type"""
    return type_of_media is None or (
        (os.path.isfile(file) or file[0:2] == "\\\\") and __match_extension(file, FileType.FILE_EXTENSIONS[type_of_media])
    )


def is_audio_file(file: str) -> bool:
    """Returns True if the file has the extension of an audio file"""
    return __match_extension(file, FileType.FILE_EXTENSIONS[FileType.AUDIO_FILE])


def is_video_file(file: str) -> bool:
    """Returns True if the file has the extension of a video file"""
    return __match_extension(file, FileType.FILE_EXTENSIONS[FileType.VIDEO_FILE])


def is_image_file(file: str) -> bool:
    """Returns True if the file has the extension of an image file"""
    return __match_extension(file, FileType.FILE_EXTENSIONS[FileType.IMAGE_FILE])


def is_media_file(file: str) -> bool:
    """Returns whether the file has an extension corresponding to media (audio/video/image) files"""
    return __match_extension(file, MEDIA_FILE_EXTENSIONS)


def get_type(file: str) -> str:
    """Returns the type of a file (audio, video, image...) from its extension"""
    for file_type, extensions in FileType.FILE_EXTENSIONS.items():
        if __match_extension(file, extensions):
            t = file_type
            break
    else:
        t = FileType.UNKNOWN_FILE
    log.logger.debug("Filetype of %s is %s", file, t)
    return t


def random_name(original_file: str, pattern: str, file_ext: str | None = None) -> str:
    """Returns a name for a file derived from another: the name of the original file, a pattern, the process id and an extension"""
    file_ext = "" if file_ext is None else f".{file_ext}"
    return f"{strip_extension(original_file)}.{pattern}.{os.getpid()}{file_ext}"
