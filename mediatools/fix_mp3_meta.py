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

"""
fix-mp3-meta: Batch fix MP3 metadata for a music library.

For each subdirectory of the root music directory, processes all audio files:
  - Determines artist and title from tags or filename
  - Normalises artist (Title Case) and title (Sentence case)
  - Determines album and track number from directory name or tags
  - Looks up release year on MusicBrainz when unknown
  - Writes ID3v1 + ID3v2 tags via mutagen
  - Sets file creation/modification timestamps to release date (YYYY-01-01 12:00)
"""

from __future__ import annotations

import os
import sys
import re
import time
import argparse
import datetime

import musicbrainzngs
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TDRC, ID3NoHeaderError
from mutagen.mp3 import MP3

from mediatools import log
import mediatools.utilities as util
import utilities.file as fil

# ---------------------------------------------------------------------------
# MusicBrainz setup
# ---------------------------------------------------------------------------
musicbrainzngs.set_useragent("audio-video-tools", "0.7", "olivier.korach@gmail.com")

# ---------------------------------------------------------------------------
# Regex patterns for directory and filename parsing
# ---------------------------------------------------------------------------
# Directory: "Artist - Album" or "Artist - Album (Year)" or "Artist"
_DIR_ARTIST_ALBUM_RE = re.compile(r"^(.+?)\s+-\s+(.+?)(?:\s*[\(\[]\s*(\d{4})\s*[\)\]])?\s*$")
# Track prefix in filename: "01 ", "01 - ", "01. ", "(01) " etc.
_TRACK_PREFIX_RE = re.compile(r"^\s*[\(\[]?(\d{1,3})[\)\].]?\s*[-.]?\s*")
# Artist - Title separator in filename
_ARTIST_TITLE_RE = re.compile(r"^(.+?)\s+-\s+(.+)$")


# ---------------------------------------------------------------------------
# Capitalisation helpers
# ---------------------------------------------------------------------------

def _title_case(text: str) -> str:
    """Every word's first letter uppercase (artist style)."""
    if not text:
        return text
    return " ".join(w.capitalize() for w in text.split())


def _sentence_case(text: str) -> str:
    """Only the very first letter uppercase, rest lowercase (track title style)."""
    if not text:
        return text
    return text[0].upper() + text[1:].lower()


# ---------------------------------------------------------------------------
# Filename / directory parsing
# ---------------------------------------------------------------------------

def _parse_dir_name(dir_name: str) -> tuple[str | None, str | None, int | None]:
    """Returns (artist, album, year) extracted from a directory base name."""
    m = _DIR_ARTIST_ALBUM_RE.match(dir_name)
    if m:
        artist = _title_case(m.group(1).strip())
        album = m.group(2).strip()
        year = int(m.group(3)) if m.group(3) else None
        return artist, album, year
    return _title_case(dir_name.strip()), None, None


def _parse_file_name(base_name: str) -> tuple[int | None, str | None, str | None]:
    """Returns (track_number, artist, title) parsed from a file base name (no extension)."""
    track: int | None = None
    artist: str | None = None
    title: str | None = None

    # Strip a leading track number if present
    tm = _TRACK_PREFIX_RE.match(base_name)
    if tm:
        track = int(tm.group(1))
        rest = base_name[tm.end():].strip()
    else:
        rest = base_name.strip()

    # Try "Artist - Title"
    am = _ARTIST_TITLE_RE.match(rest)
    if am:
        artist = _title_case(am.group(1).strip())
        title = _sentence_case(am.group(2).strip())
    else:
        title = _sentence_case(rest) or None

    return track, artist, title


# ---------------------------------------------------------------------------
# MusicBrainz lookup
# ---------------------------------------------------------------------------

def _mb_lookup_release(artist: str, album: str) -> tuple[int | None, list[str]]:
    """Returns (year, [track_title, ...]) from MusicBrainz for the best-matching release."""
    if not artist or not album:
        return None, []
    try:
        result = musicbrainzngs.search_releases(artist=artist, release=album, limit=3)
        releases = result.get("release-list", [])
        if not releases:
            return None, []
        rel = releases[0]
        year = None
        date_str = rel.get("date", "")
        if date_str:
            try:
                year = int(date_str[:4])
            except ValueError:
                pass
        # Fetch full release with tracklist
        release_id = rel["id"]
        full = musicbrainzngs.get_release_by_id(release_id, includes=["recordings"])
        tracks: list[str] = []
        for medium in full.get("release", {}).get("medium-list", []):
            for track in medium.get("track-list", []):
                tracks.append(track.get("recording", {}).get("title", ""))
        return year, tracks
    except Exception as e:
        log.logger.warning("MusicBrainz lookup failed for '%s' / '%s': %s", artist, album, str(e))
        return None, []


def _mb_lookup_track(artist: str, title: str) -> int | None:
    """Returns the release year for a specific recording from MusicBrainz."""
    if not artist or not title:
        return None
    try:
        result = musicbrainzngs.search_recordings(artist=artist, recording=title, limit=3)
        recordings = result.get("recording-list", [])
        for rec in recordings:
            for release in rec.get("release-list", []):
                date_str = release.get("date", "")
                if date_str:
                    try:
                        return int(date_str[:4])
                    except ValueError:
                        pass
    except Exception as e:
        log.logger.warning("MusicBrainz recording lookup failed for '%s' / '%s': %s", artist, title, str(e))
    return None


# ---------------------------------------------------------------------------
# ID3 tag writing
# ---------------------------------------------------------------------------

def _write_tags(filepath: str, artist: str | None, title: str | None, album: str | None, track: int | None, year: int | None) -> None:
    """Writes ID3v1 and ID3v2 tags to an MP3 file using mutagen."""
    try:
        try:
            tags = ID3(filepath)
        except ID3NoHeaderError:
            tags = ID3()

        if artist:
            tags["TPE1"] = TPE1(encoding=3, text=artist)
        if title:
            tags["TIT2"] = TIT2(encoding=3, text=title)
        if album:
            tags["TALB"] = TALB(encoding=3, text=album)
        if track is not None:
            tags["TRCK"] = TRCK(encoding=3, text=str(track))
        if year is not None:
            tags["TDRC"] = TDRC(encoding=3, text=str(year))

        # Save ID3v2.3 (most compatible) + ID3v1 header
        tags.save(filepath, v1=2, v2_version=3)
        log.logger.info("Tags written: %s | artist=%s title=%s album=%s track=%s year=%s", filepath, artist, title, album, track, year)
    except Exception as e:
        log.logger.error("Failed to write tags for %s: %s", filepath, str(e))


# ---------------------------------------------------------------------------
# File timestamp setting
# ---------------------------------------------------------------------------

def _set_file_date(filepath: str, year: int) -> None:
    """Sets file creation and modification timestamps to YYYY-01-01 12:00:00."""
    try:
        dt = datetime.datetime(year, 1, 1, 12, 0, 0)
        ts = dt.timestamp()
        os.utime(filepath, (ts, ts))
        log.logger.info("Set file date of %s to %d-01-01 12:00", filepath, year)
    except Exception as e:
        log.logger.error("Failed to set file date for %s: %s", filepath, str(e))


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------

def _process_file(filepath: str, dir_artist: str | None, dir_album: str | None, dir_year: int | None, mb_tracks: list[str], dry_run: bool) -> None:
    """Processes a single audio file: reads tags, fills in gaps, writes tags."""
    base = os.path.splitext(os.path.basename(filepath))[0]

    # 1. Parse filename for track#, artist, title
    fn_track, fn_artist, fn_title = _parse_file_name(base)

    # 2. Read existing tags via mutagen
    existing_artist, existing_title, existing_album, existing_track, existing_year = None, None, None, None, None
    try:
        audio = MP3(filepath)
        if audio.tags:
            existing_artist = str(audio.tags.get("TPE1", "")).strip() or None
            existing_title = str(audio.tags.get("TIT2", "")).strip() or None
            existing_album = str(audio.tags.get("TALB", "")).strip() or None
            existing_track_raw = str(audio.tags.get("TRCK", "")).strip()
            if existing_track_raw:
                try:
                    existing_track = int(existing_track_raw.split("/")[0])
                except ValueError:
                    pass
            existing_year_raw = str(audio.tags.get("TDRC", "")).strip()
            if existing_year_raw:
                try:
                    existing_year = int(existing_year_raw[:4])
                except ValueError:
                    pass
    except Exception as e:
        log.logger.warning("Could not read tags from %s: %s", filepath, str(e))

    # 3. Resolve final values: prefer existing tag, fall back to filename parse, then directory info
    artist = existing_artist or fn_artist or dir_artist
    title = existing_title or fn_title
    album = existing_album or dir_album
    track = existing_track or fn_track
    year = existing_year or dir_year

    # 4. Try to match title against MusicBrainz track list (if album was looked up)
    if not title and track is not None and mb_tracks and (track - 1) < len(mb_tracks):
        title = _sentence_case(mb_tracks[track - 1])

    # 5. MusicBrainz lookup for year if still missing
    if year is None and artist and album:
        mb_year, _ = _mb_lookup_release(artist, album)
        year = mb_year
    if year is None and artist and title:
        year = _mb_lookup_track(artist, title)

    # 6. Normalise capitalisation
    if artist:
        artist = _title_case(artist)
    if title:
        title = _sentence_case(title)

    log.logger.info("File: %s  artist=%s  title=%s  album=%s  track=%s  year=%s", base, artist, title, album, track, year)

    if dry_run:
        return

    # 7. Write tags
    _write_tags(filepath, artist, title, album, track, year)

    # 8. Set file timestamp
    if year:
        _set_file_date(filepath, year)


# ---------------------------------------------------------------------------
# Per-directory processing
# ---------------------------------------------------------------------------

def _process_directory(dirpath: str, dry_run: bool) -> None:
    """Processes all audio files in a single directory."""
    dir_name = os.path.basename(dirpath)
    dir_artist, dir_album, dir_year = _parse_dir_name(dir_name)
    log.logger.info("Directory: %s  →  artist=%s  album=%s  year=%s", dir_name, dir_artist, dir_album, dir_year)

    # MusicBrainz album lookup (once per directory)
    mb_tracks: list[str] = []
    if dir_artist and dir_album and dir_year is None:
        mb_year, mb_tracks = _mb_lookup_release(dir_artist, dir_album)
        if mb_year and dir_year is None:
            dir_year = mb_year

    audio_files = sorted(
        [os.path.join(dirpath, f) for f in os.listdir(dirpath) if fil.is_audio_file(f)],
        key=lambda p: os.path.basename(p).lower(),
    )
    log.logger.info("Found %d audio file(s) in %s", len(audio_files), dirpath)

    for filepath in audio_files:
        _process_file(filepath, dir_artist, dir_album, dir_year, mb_tracks, dry_run)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    util.init("fix-mp3-meta")
    parser = argparse.ArgumentParser(description="Fix MP3 metadata tags for a music library")
    parser.add_argument("-d", "--directory", default=r"E:\Musique", help="Root music directory (default: E:\\Musique)")
    parser.add_argument("--dry-run", action="store_true", help="Parse and log actions without writing tags or changing timestamps")
    parser.add_argument("-g", "--debug", required=False, type=int, help="Debug level")
    args = parser.parse_args()

    if args.debug:
        util.set_debug_level(args.debug)

    root = args.directory
    if not os.path.isdir(root):
        log.logger.error("Directory not found: %s", root)
        sys.exit(1)

    dry_run = args.dry_run
    if dry_run:
        log.logger.info("DRY RUN mode — no files will be modified")

    # Process each immediate subdirectory
    subdirs = sorted([os.path.join(root, d) for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))])
    log.logger.info("Processing %d subdirectories under %s", len(subdirs), root)

    for subdir in subdirs:
        log.logger.info("=== Processing directory: %s ===", subdir)
        try:
            _process_directory(subdir, dry_run)
        except Exception as e:
            log.logger.error("Error processing %s: %s", subdir, str(e))

    # Also process audio files directly in the root (if any)
    root_audio = [os.path.join(root, f) for f in os.listdir(root) if fil.is_audio_file(f)]
    if root_audio:
        log.logger.info("Processing %d audio file(s) directly in root", len(root_audio))
        _process_directory(root, dry_run)

    log.logger.info("Done.")
    sys.exit(0)


if __name__ == "__main__":
    main()
