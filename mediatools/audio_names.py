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

"""Code shared by the tools that fix the metadata of a music library album by album (fix-mp3-meta, audio-normalize):
parsing of the names of the directories and of the files, and walk through the directories given as input"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

import utilities.file as fil
from mediatools import log

_BITRATE_RE = re.compile(r"\d\s*k", re.IGNORECASE)


def strip_encoding_postfix(base_name: str) -> str:
    """Removes a trailing bitrate/codec postfix, like " (128kbit_AAC)" or " [320kbps MP3]", from a file base name:
    it is the last bracketed text (without nested brackets) when it contains a number followed by k"""
    name = base_name.rstrip()
    if name[-1:] not in (")", "]"):
        return name
    opening = max(name.rfind("("), name.rfind("["))
    inner = name[opening + 1 : -1]
    if opening < 0 or any(c in inner for c in "()[]") or not _BITRATE_RE.search(inner):
        return name
    return name[:opening].rstrip()


if TYPE_CHECKING:
    from collections.abc import Callable

# Track prefix in filename: "01 ", "01 - ", "01. ", "(01) " etc.
_TRACK_PREFIX_RE = re.compile(r"^\s*[\(\[]?(\d{1,3})[\)\].]?\s*[-.]?\s*")


def _split_on_dash(text: str) -> tuple[str, int] | None:
    """Splits a text at its first " - " separator: a dash surrounded by whitespace, with at least 1 character before and after.
    Returns the text before the separator and the index of the text after it, or None if there is no separator"""
    size = len(text)
    dash = text.find("-", 2)
    while dash != -1:
        if text[dash - 1].isspace() and dash + 1 < size and text[dash + 1].isspace():
            before = dash - 1
            while before > 1 and text[before - 1].isspace():
                before -= 1
            after = dash + 1
            while after < size and text[after].isspace():
                after += 1
            if after < size or after - dash > 2:
                return text[:before], min(after, size - 1)
        dash = text.find("-", dash + 1)
    return None


def _split_year(text: str) -> tuple[str, int | None]:
    """Splits an album and its optional year, eg "Album (1999)" or "Album [1999]"""
    trimmed = text.rstrip()
    if trimmed[-1:] in (")", "]"):
        opening = max(trimmed.rfind("("), trimmed.rfind("["))
        year = trimmed[opening + 1 : -1].strip()
        if opening > 0 and len(year) == 4 and year.isdecimal():
            return trimmed[:opening], int(year)
    return trimmed, None


def title_case(text: str) -> str:
    """Every word's first letter uppercase (artist style)."""
    if not text:
        return text
    return " ".join(w.capitalize() for w in text.split())


def sentence_case(text: str) -> str:
    """Only the very first letter uppercase, rest lowercase (track title style)."""
    if not text:
        return text
    return text[0].upper() + text[1:].lower()


def parse_dir_name(dir_name: str) -> tuple[str | None, str | None, int | None]:
    """Returns (artist, album, year) extracted from a directory base name."""
    separator = _split_on_dash(dir_name)
    if separator:
        album, year = _split_year(dir_name[separator[1] :])
        return title_case(separator[0].strip()), album.strip(), year
    return title_case(dir_name.strip()), None, None


def parse_file_name(base_name: str) -> tuple[int | None, str | None, str | None]:
    """Returns (track_number, artist, title) parsed from a file base name (no extension)."""
    track: int | None = None
    artist: str | None = None
    title: str | None = None

    # Strip a leading track number if present
    tm = _TRACK_PREFIX_RE.match(base_name)
    if tm:
        track = int(tm.group(1))
        end = tm.end()
        rest = base_name[end:].strip()
    else:
        rest = base_name.strip()

    # Try "Artist - Title"
    separator = _split_on_dash(rest)
    if separator:
        artist = title_case(separator[0].strip())
        title = sentence_case(rest[separator[1] :].strip())
    else:
        title = sentence_case(rest) or None

    return track, artist, title


def collect_inputs(inputs: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """Splits the files and directories given as input into the directories to process and the loose audio files
    grouped by their parent directory"""
    dirs_to_process: list[str] = []
    files_by_dir: dict[str, list[str]] = {}
    for entry in inputs:
        entry = os.path.abspath(entry)
        if os.path.isdir(entry):
            dirs_to_process.append(entry)
        elif fil.is_audio_file(entry):
            files_by_dir.setdefault(os.path.dirname(entry), []).append(entry)
        else:
            log.logger.warning("Skipping %s: not a directory or audio file", entry)
    return dirs_to_process, files_by_dir


def process_album_directories(dirs_to_process: list[str], process_directory: Callable[[str, bool], None], dry_run: bool) -> None:
    """For each directory: processes each of its immediate sub-directories (an album), then the audio files at its root level"""
    for root in sorted(dirs_to_process):
        if not os.path.isdir(root):
            log.logger.error("Directory not found: %s", root)
            continue
        subdirs = sorted([os.path.join(root, d) for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))])
        root_audio = [os.path.join(root, f) for f in os.listdir(root) if fil.is_audio_file(f)]
        if subdirs:
            log.logger.info("Processing %d subdirectories under %s", len(subdirs), root)
            for subdir in subdirs:
                log.logger.info("=== Processing directory: %s ===", subdir)
                try:
                    process_directory(subdir, dry_run)
                except Exception as e:
                    log.logger.error("Error processing %s: %s", subdir, str(e))
        if root_audio:
            log.logger.info("Processing %d audio file(s) directly in %s", len(root_audio), root)
            process_directory(root, dry_run)
