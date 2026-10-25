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

if TYPE_CHECKING:
    from collections.abc import Callable

# Directory: "Artist - Album" or "Artist - Album (Year)" or "Artist"
_DIR_ARTIST_ALBUM_RE = re.compile(r"^(.+?)\s+-\s+(.+?)(?:\s*[\(\[]\s*(\d{4})\s*[\)\]])?\s*$")
# Track prefix in filename: "01 ", "01 - ", "01. ", "(01) " etc.
_TRACK_PREFIX_RE = re.compile(r"^\s*[\(\[]?(\d{1,3})[\)\].]?\s*[-.]?\s*")
# Artist - Title separator in filename
_ARTIST_TITLE_RE = re.compile(r"^(.+?)\s+-\s+(.+)$")


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
    m = _DIR_ARTIST_ALBUM_RE.match(dir_name)
    if m:
        artist = title_case(m.group(1).strip())
        album = m.group(2).strip()
        year = int(m.group(3)) if m.group(3) else None
        return artist, album, year
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
    am = _ARTIST_TITLE_RE.match(rest)
    if am:
        artist = title_case(am.group(1).strip())
        title = sentence_case(am.group(2).strip())
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
