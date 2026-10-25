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

"""fix-mp3-meta: Batch fix MP3 metadata for a music library.

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
import argparse
import datetime as dt

import musicbrainzngs
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TDRC, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

from mediatools import log, version
from mediatools.audio_names import title_case, sentence_case, parse_dir_name, parse_file_name, collect_inputs, process_album_directories
from mediatools import metacopy
import mediatools.utilities as util
import utilities.file as fil

_M4A_TAG_MAP = {"artist": "©ART", "title": "©nam", "album": "©alb", "year": "©day", "track": "trkn"}

# ---------------------------------------------------------------------------
# MusicBrainz setup
# ---------------------------------------------------------------------------
musicbrainzngs.set_useragent("audio-video-tools", version.MEDIA_TOOLS_VERSION, "olivier.korach@gmail.com")

# ---------------------------------------------------------------------------
# MusicBrainz lookup
# ---------------------------------------------------------------------------


def mb_lookup_release(artist: str, album: str) -> tuple[int | None, list[str]]:
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
            tracks.extend(track.get("recording", {}).get("title", "") for track in medium.get("track-list", []))
        return year, tracks
    except Exception as e:
        log.logger.warning("MusicBrainz lookup failed for '%s' / '%s': %s", artist, album, str(e))
        return None, []


def mb_lookup_track(artist: str, title: str) -> int | None:
    """Returns the release year for a specific recording from MusicBrainz."""
    if not artist or not title:
        return None
    try:
        result = musicbrainzngs.search_recordings(artist=artist, recording=title, limit=3)
        recordings = result.get("recording-list", [])
        for rec in recordings:
            for release in rec.get("release-list", []):
                year = _to_int(release.get("date", ""), 4)
                if year is not None:
                    return year
    except Exception as e:
        log.logger.warning("MusicBrainz recording lookup failed for '%s' / '%s': %s", artist, title, str(e))
    return None


# ---------------------------------------------------------------------------
# Tag reading / writing (MP3 via ID3, M4A via MP4 atoms)
# ---------------------------------------------------------------------------


def is_m4a(filepath: str) -> bool:
    """Returns True if the file is an m4a or aac file"""
    return fil.extension(filepath).lower() in ("m4a", "aac")


def _to_int(text: str, length: int | None = None) -> int | None:
    """Converts the beginning of a text (its first characters) to an integer, None if it is not one"""
    try:
        return int(text[:length])
    except ValueError:
        return None


def _read_m4a_tags(filepath: str) -> tuple[str | None, str | None, str | None, int | None, int | None]:
    """Returns (artist, title, album, track, year) from the tags of an m4a file."""
    tags = MP4(filepath).tags or {}

    def text(key: str) -> str:
        """Returns the stripped text of a tag, an empty string if it is not set"""
        return (tags.get(_M4A_TAG_MAP[key], [None])[0] or "").strip()

    track = None
    trkn = tags.get(_M4A_TAG_MAP["track"], None)
    if trkn:
        try:
            track = int(trkn[0][0])
        except (ValueError, IndexError, TypeError):
            pass
    year = _to_int(text("year"), 4) if text("year") else None
    return text("artist") or None, text("title") or None, text("album") or None, track, year


def _read_mp3_tags(filepath: str) -> tuple[str | None, str | None, str | None, int | None, int | None]:
    """Returns (artist, title, album, track, year) from the ID3 tags of an mp3 file."""
    audio = MP3(filepath)
    if not audio.tags:
        return None, None, None, None, None

    def text(frame: str) -> str:
        """Returns the stripped text of a frame, an empty string if it is not set"""
        return str(audio.tags.get(frame, "")).strip()

    track = _to_int(text("TRCK").split("/", maxsplit=1)[0]) if text("TRCK") else None
    year = _to_int(text("TDRC"), 4) if text("TDRC") else None
    return text("TPE1") or None, text("TIT2") or None, text("TALB") or None, track, year


def read_existing_tags(filepath: str) -> tuple[str | None, str | None, str | None, int | None, int | None]:
    """Returns (artist, title, album, track, year) from existing file tags."""
    try:
        return _read_m4a_tags(filepath) if is_m4a(filepath) else _read_mp3_tags(filepath)
    except Exception as e:
        log.logger.warning("Could not read tags from %s: %s", filepath, str(e))
    return None, None, None, None, None


@metacopy.keeps_dates
def write_tags(filepath: str, *, artist: str | None, title: str | None, album: str | None, track: int | None, year: int | None) -> None:
    """Writes tags to an audio file — ID3v1+v2 for MP3, iTunes atoms for M4A."""
    try:
        if is_m4a(filepath):
            audio = MP4(filepath)
            if audio.tags is None:
                audio.add_tags()
            if artist:
                audio.tags[_M4A_TAG_MAP["artist"]] = [artist]
            if title:
                audio.tags[_M4A_TAG_MAP["title"]] = [title]
            if album:
                audio.tags[_M4A_TAG_MAP["album"]] = [album]
            if track is not None:
                audio.tags[_M4A_TAG_MAP["track"]] = [(track, 0)]
            if year is not None:
                audio.tags[_M4A_TAG_MAP["year"]] = [str(year)]
            audio.save()
        else:
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


def set_file_date(filepath: str, year: int) -> None:
    """Sets file creation and modification timestamps to YYYY-01-01 12:00:00."""
    try:
        file_time = dt.datetime(year, 1, 1, 12, 0, 0)
        ts = file_time.timestamp()
        os.utime(filepath, (ts, ts))
        log.logger.info("Set file date of %s to %d-01-01 12:00", filepath, year)
    except Exception as e:
        log.logger.error("Failed to set file date for %s: %s", filepath, str(e))


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------


def process_file(filepath: str, dir_artist: str | None, dir_album: str | None, dir_year: int | None, mb_tracks: list[str], *, dry_run: bool) -> None:
    """Processes a single audio file: reads tags, fills in gaps, writes tags."""
    base = os.path.splitext(os.path.basename(filepath))[0]

    # 1. Parse filename for track#, artist, title
    fn_track, fn_artist, fn_title = parse_file_name(base)

    # 2. Read existing tags via mutagen (handles both MP3 and M4A)
    existing_artist, existing_title, existing_album, existing_track, existing_year = read_existing_tags(filepath)

    # 3. Resolve final values: prefer existing tag, fall back to filename parse, then directory info
    artist = existing_artist or fn_artist or dir_artist
    title = existing_title or fn_title
    album = existing_album or dir_album
    track = existing_track or fn_track
    year = existing_year or dir_year

    # 4. Try to match title against MusicBrainz track list (if album was looked up)
    if not title and track is not None and mb_tracks and (track - 1) < len(mb_tracks):
        title = sentence_case(mb_tracks[track - 1])

    # 5. MusicBrainz lookup for year if still missing
    if year is None and artist and album:
        mb_year, _ = mb_lookup_release(artist, album)
        year = mb_year
    if year is None and artist and title:
        year = mb_lookup_track(artist, title)

    # 6. Normalise capitalisation
    if artist:
        artist = title_case(artist)
    if title:
        title = sentence_case(title)

    log.logger.info("File: %s  artist=%s  title=%s  album=%s  track=%s  year=%s", base, artist, title, album, track, year)

    if dry_run:
        return

    # 7. Write tags
    write_tags(filepath, artist=artist, title=title, album=album, track=track, year=year)

    # 8. Set file timestamp
    if year:
        set_file_date(filepath, year)


# ---------------------------------------------------------------------------
# Per-directory processing
# ---------------------------------------------------------------------------


def process_directory(dirpath: str, dry_run: bool) -> None:
    """Processes all audio files in a single directory."""
    dir_name = os.path.basename(dirpath)
    dir_artist, dir_album, dir_year = parse_dir_name(dir_name)
    log.logger.info("Directory: %s  →  artist=%s  album=%s  year=%s", dir_name, dir_artist, dir_album, dir_year)

    # MusicBrainz album lookup (once per directory)
    mb_tracks: list[str] = []
    if dir_artist and dir_album and dir_year is None:
        mb_year, mb_tracks = mb_lookup_release(dir_artist, dir_album)
        if mb_year and dir_year is None:
            dir_year = mb_year

    audio_files = sorted(
        [os.path.join(dirpath, f) for f in os.listdir(dirpath) if fil.is_audio_file(f)],
        key=lambda p: os.path.basename(p).lower(),
    )
    log.logger.info("Found %d audio file(s) in %s", len(audio_files), dirpath)

    progress = util.GlobalProgress(len(audio_files))
    for filepath in audio_files:
        process_file(filepath, dir_artist, dir_album, dir_year, mb_tracks, dry_run=dry_run)
        progress.done()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Fixes the tags of the mp3 and m4a files of a music library from the names of the files and directories"""
    util.init("fix-mp3-meta")
    parser = argparse.ArgumentParser(description="Fix MP3 metadata tags for a music library")
    util.add_input_args(
        parser,
        "Files and/or directories to process (default: E:\\Musique). -f/--files is a deprecated alias",
        required=False,
        dest="files",
        aliases=("-f", "--files"),
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and log actions without writing tags or changing timestamps")
    util.add_verbosity_arg(parser)
    args = parser.parse_args()

    util.set_debug_level(util.get_verbosity(vars(args)))

    inputs = args.files or [r"E:\Musique"]
    dry_run = args.dry_run
    if dry_run:
        log.logger.info("DRY RUN mode — no files will be modified")

    dirs_to_process, files_by_dir = collect_inputs(inputs)
    process_album_directories(dirs_to_process, process_directory, dry_run)

    # For individual files: process them with the context of their parent directory
    for parent, file_list in sorted(files_by_dir.items()):
        dir_artist, dir_album, dir_year = parse_dir_name(os.path.basename(parent))
        mb_tracks: list[str] = []
        if dir_artist and dir_album and dir_year is None:
            mb_year, mb_tracks = mb_lookup_release(dir_artist, dir_album)
            if mb_year:
                dir_year = mb_year
        log.logger.info("Processing %d file(s) from %s", len(file_list), parent)
        for filepath in sorted(file_list):
            try:
                process_file(filepath, dir_artist, dir_album, dir_year, mb_tracks, dry_run=dry_run)
            except Exception as e:
                log.logger.error("Error processing %s: %s", filepath, str(e))

    log.logger.info("Done.")
    sys.exit(0)


if __name__ == "__main__":
    main()
