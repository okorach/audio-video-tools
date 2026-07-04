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
audio-normalize: Comprehensive audio metadata normalizer.

For each audio file:
  - Determines artist, title, album, track from tags or filename/directory name
  - Normalises capitalisation (artist → Title Case, title → Sentence case)
  - Looks up MusicBrainz for release date (exact YYYY-MM-DD when available), genre, cover art
  - Embeds cover art in the file; saves folder.jpg (max 600×600) for album folders
  - Encodes genre using ID3v1 genres (0–79) + Winamp extensions (80–147)
  - Writes tags for MP3 (ID3v1.1 + ID3v2.3), M4A, OGG, OPUS, FLAC
  - Sets file timestamps to the exact (or approximate) release date
  - Cleans up the filename: strips encoding postfixes and exotic Unicode characters
"""

from __future__ import annotations

import base64
import datetime
from dataclasses import dataclass, field as dc_field
import io
import os
import re
import sys
import unicodedata
import argparse

import musicbrainzngs
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TDRC, APIC, TCON, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture as FlacPicture

try:
    from PIL import Image as PilImage

    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

from mediatools import log
import mediatools.utilities as util
import utilities.file as fil


# ---------------------------------------------------------------------------
# Tag data container
# ---------------------------------------------------------------------------


@dataclass
class AudioTags:
    """Bundles all writable audio metadata for a single file."""

    artist: str | None = None
    title: str | None = None
    album: str | None = None
    track: int | None = None
    year: int | None = None
    genre: str | None = None
    cover_bytes: bytes | None = dc_field(default=None, repr=False)


# ---------------------------------------------------------------------------
# MusicBrainz setup
# ---------------------------------------------------------------------------
musicbrainzngs.set_useragent("audio-video-tools", "0.7", "olivier.korach@gmail.com")

# ---------------------------------------------------------------------------
# ID3v1 genres 0–79 (standard) + Winamp extensions 80–147
# ---------------------------------------------------------------------------
_ID3V1_GENRES: list[str] = [
    # 0–9
    "Blues",
    "Classic Rock",
    "Country",
    "Dance",
    "Disco",
    "Funk",
    "Grunge",
    "Hip-Hop",
    "Jazz",
    "Metal",
    # 10–19
    "New Age",
    "Oldies",
    "Other",
    "Pop",
    "Rhythm and Blues",
    "Rap",
    "Reggae",
    "Rock",
    "Techno",
    "Industrial",
    # 20–29
    "Alternative",
    "Ska",
    "Death Metal",
    "Pranks",
    "Soundtrack",
    "Euro-Techno",
    "Ambient",
    "Trip-Hop",
    "Vocal",
    "Jazz & Funk",
    # 30–39
    "Fusion",
    "Trance",
    "Classical",
    "Instrumental",
    "Acid",
    "House",
    "Game",
    "Sound Clip",
    "Gospel",
    "Noise",
    # 40–49
    "Alternative Rock",
    "Bass",
    "Soul",
    "Punk",
    "Space",
    "Meditative",
    "Instrumental Pop",
    "Instrumental Rock",
    "Ethnic",
    "Gothic",
    # 50–59
    "Darkwave",
    "Techno-Industrial",
    "Electronic",
    "Pop-Folk",
    "Eurodance",
    "Dream",
    "Southern Rock",
    "Comedy",
    "Cult",
    "Gangsta",
    # 60–69
    "Top 40",
    "Christian Rap",
    "Pop/Funk",
    "Jungle",
    "Native US",
    "Cabaret",
    "New Wave",
    "Psychedelic",
    "Rave",
    "Showtunes",
    # 70–79
    "Trailer",
    "Lo-Fi",
    "Tribal",
    "Acid Punk",
    "Acid Jazz",
    "Polka",
    "Retro",
    "Musical",
    "Rock & Roll",
    "Hard Rock",
    # 80–89 (Winamp)
    "Folk",
    "Folk-Rock",
    "National Folk",
    "Swing",
    "Fast Fusion",
    "Bebop",
    "Latin",
    "Revival",
    "Celtic",
    "Bluegrass",
    # 90–99
    "Avantgarde",
    "Gothic Rock",
    "Progressive Rock",
    "Psychedelic Rock",
    "Symphonic Rock",
    "Slow Rock",
    "Big Band",
    "Chorus",
    "Easy Listening",
    "Acoustic",
    # 100–109
    "Humour",
    "Speech",
    "Chanson",
    "Opera",
    "Chamber Music",
    "Sonata",
    "Symphony",
    "Booty Bass",
    "Primus",
    "Porn Groove",
    # 110–119
    "Satire",
    "Slow Jam",
    "Club",
    "Tango",
    "Samba",
    "Folklore",
    "Ballad",
    "Power Ballad",
    "Rhythmic Soul",
    "Freestyle",
    # 120–129
    "Duet",
    "Punk Rock",
    "Drum Solo",
    "A Cappella",
    "Euro-House",
    "Dance Hall",
    "Goa",
    "Drum & Bass",
    "Club-House",
    "Hardcore Techno",
    # 130–139
    "Terror",
    "Indie",
    "BritPop",
    "Negerpunk",
    "Polsk Punk",
    "Beat",
    "Christian Gangsta Rap",
    "Heavy Metal",
    "Black Metal",
    "Crossover",
    # 140–147
    "Contemporary Christian",
    "Christian Rock",
    "Merengue",
    "Salsa",
    "Thrash Metal",
    "Anime",
    "JPop",
    "Synthpop",
]
_GENRE_LOWER: dict[str, int] = {g.lower(): i for i, g in enumerate(_ID3V1_GENRES)}

# Encoding postfix pattern (e.g. "(128kbit_AAC)", "[320kbps MP3]")
_ENCODING_POSTFIX_RE = re.compile(r"\s*[\(\[][^()\[\]]*\d+\s*k(?:bit|bps|b)?[^()\[\]]*[\)\]]\s*$", re.IGNORECASE)

# Directory: "Artist - Album" or "Artist - Album (Year)" or "Artist"
_DIR_ARTIST_ALBUM_RE = re.compile(r"^(.+?)\s+-\s+(.+?)(?:\s*[\(\[]\s*(\d{4})\s*[\)\]])?\s*$")
# Track prefix: "01 ", "01 - ", "01. ", "(01) " etc.
_TRACK_PREFIX_RE = re.compile(r"^\s*[\(\[]?(\d{1,3})[\)\].]?\s*[-.]?\s*")
# Artist - Title separator
_ARTIST_TITLE_RE = re.compile(r"^(.+?)\s+-\s+(.+)$")

_COVER_FILENAME = "folder.jpg"
_MAX_COVER_SIZE = 600


# ---------------------------------------------------------------------------
# Genre helpers
# ---------------------------------------------------------------------------


def _find_genre(genre_name: str) -> str | None:
    """Returns the canonical genre name if it matches an ID3v1 genre (0–147), else None."""
    if not genre_name:
        return None
    idx = _GENRE_LOWER.get(genre_name.lower().strip())
    if idx is not None:
        return _ID3V1_GENRES[idx]
    # Fuzzy: try if any known genre starts with the given name
    for name, i in _GENRE_LOWER.items():
        if name.startswith(genre_name.lower().strip()):
            return _ID3V1_GENRES[i]
    return None


# ---------------------------------------------------------------------------
# Filename cleanup
# ---------------------------------------------------------------------------


def _strip_encoding_postfix(base_name: str) -> str:
    """Remove encoding postfixes like '(128kbit_AAC)' or '[320kbps MP3]'."""
    return _ENCODING_POSTFIX_RE.sub("", base_name).rstrip()


def _strip_exotic_unicode(text: str) -> str:
    """Replace non-ASCII chars with ASCII equivalents (via NFKD decomposition) or remove them."""
    # Decompose (é → e + combining accent) then drop combining marks
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in decomposed if unicodedata.category(c) != "Mn" and ord(c) < 128)
    # Collapse multiple spaces/underscores left by removed chars
    return re.sub(r"[ _]{2,}", " ", ascii_only).strip()


def _clean_basename(base_name: str) -> str:
    """Return a cleaned file base name (no extension): strip postfixes and exotic unicode."""
    return _strip_exotic_unicode(_strip_encoding_postfix(base_name))


# ---------------------------------------------------------------------------
# Capitalisation helpers
# ---------------------------------------------------------------------------


def _title_case(text: str) -> str:
    if not text:
        return text
    return " ".join(w.capitalize() for w in text.split())


def _sentence_case(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:].lower()


# ---------------------------------------------------------------------------
# Filename / directory parsing
# ---------------------------------------------------------------------------


def _parse_dir_name(dir_name: str) -> tuple[str | None, str | None, int | None]:
    """Returns (artist, album, year) from a directory base name."""
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

    tm = _TRACK_PREFIX_RE.match(base_name)
    if tm:
        track = int(tm.group(1))
        rest = base_name[tm.end() :].strip()
    else:
        rest = base_name.strip()

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


def _parse_mb_date(date_str: str) -> tuple[int | None, datetime.date | None]:
    """Parse a MusicBrainz date string (YYYY, YYYY-MM, YYYY-MM-DD) into (year, date)."""
    if not date_str:
        return None, None
    parts = date_str.split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return year, datetime.date(year, month, day)
    except (ValueError, IndexError):
        return None, None


def _extract_genre_from_release(release: dict) -> str | None:
    """Return the first recognisable genre from a MusicBrainz release dict."""
    for g in release.get("genre-list", []):
        candidate = _find_genre(g.get("name", ""))
        if candidate:
            return candidate
    for t in release.get("tag-list", []):
        candidate = _find_genre(t.get("name", ""))
        if candidate:
            return candidate
    return None


def _extract_tracks_from_release(release: dict) -> list[str]:
    """Return a flat list of recording titles from a MusicBrainz release dict."""
    tracks: list[str] = []
    for medium in release.get("medium-list", []):
        for track in medium.get("track-list", []):
            tracks.append(track.get("recording", {}).get("title", ""))
    return tracks


def _mb_lookup_release(artist: str, album: str) -> tuple[int | None, datetime.date | None, str | None, list[str], str | None]:
    """Returns (year, exact_date, genre, track_titles, release_id) for the best MusicBrainz match."""
    if not artist or not album:
        return None, None, None, [], None
    try:
        result = musicbrainzngs.search_releases(artist=artist, release=album, limit=3)
        releases = result.get("release-list", [])
        if not releases:
            return None, None, None, [], None
        rel = releases[0]
        release_id = rel["id"]
        year, exact_date = _parse_mb_date(rel.get("date", ""))
        full = musicbrainzngs.get_release_by_id(release_id, includes=["recordings", "genres", "tags"])
        release = full.get("release", {})
        full_date_str = release.get("date", "")
        if full_date_str:
            year, exact_date = _parse_mb_date(full_date_str)
        genre = _extract_genre_from_release(release)
        tracks = _extract_tracks_from_release(release)
        return year, exact_date, genre, tracks, release_id
    except Exception as e:
        log.logger.warning("MusicBrainz lookup failed for '%s' / '%s': %s", artist, album, str(e))
        return None, None, None, [], None


def _mb_lookup_track(artist: str, title: str) -> tuple[int | None, datetime.date | None]:
    """Returns (year, exact_date) for a specific recording from MusicBrainz."""
    if not artist or not title:
        return None, None
    try:
        result = musicbrainzngs.search_recordings(artist=artist, recording=title, limit=3)
        for rec in result.get("recording-list", []):
            for release in rec.get("release-list", []):
                year, exact_date = _parse_mb_date(release.get("date", ""))
                if year:
                    return year, exact_date
    except Exception as e:
        log.logger.warning("MusicBrainz recording lookup failed for '%s' / '%s': %s", artist, title, str(e))
    return None, None


# ---------------------------------------------------------------------------
# Cover art
# ---------------------------------------------------------------------------


def _fetch_cover_art(release_id: str) -> bytes | None:
    """Fetch the front cover image bytes from MusicBrainz Cover Art Archive."""
    if not release_id:
        return None
    try:
        data = musicbrainzngs.get_image_front(release_id, size="500")
        if isinstance(data, bytes) and len(data) > 0:
            return data
    except Exception as e:
        log.logger.debug("Cover art not available for %s: %s", release_id, str(e))
    return None


def _resize_image(image_bytes: bytes, max_size: int = _MAX_COVER_SIZE) -> bytes:
    """Resize image so neither dimension exceeds max_size. Requires Pillow."""
    if not _PIL_AVAILABLE:
        return image_bytes
    try:
        img = PilImage.open(io.BytesIO(image_bytes))
        if img.width > max_size or img.height > max_size:
            resample = getattr(PilImage, "Resampling", PilImage).LANCZOS
            img.thumbnail((max_size, max_size), resample)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception as e:
        log.logger.warning("Image resize failed: %s", str(e))
        return image_bytes


def _save_cover_to_folder(dirpath: str, image_bytes: bytes) -> None:
    """Save cover art as folder.jpg (max 600×600) in the given directory."""
    cover_path = os.path.join(dirpath, _COVER_FILENAME)
    try:
        resized = _resize_image(image_bytes)
        with open(cover_path, "wb") as f:
            f.write(resized)
        log.logger.info("Saved cover art to %s", cover_path)
    except Exception as e:
        log.logger.error("Failed to save cover art to %s: %s", cover_path, str(e))


def _make_flac_picture(image_bytes: bytes) -> FlacPicture:
    pic = FlacPicture()
    pic.type = 3  # Front cover
    pic.mime = "image/jpeg"
    pic.data = image_bytes
    return pic


# ---------------------------------------------------------------------------
# Audio format detection
# ---------------------------------------------------------------------------

_VORBIS_COMMENT_FORMATS = ("ogg", "opus", "flac", "oga")


def _audio_format(filepath: str) -> str:
    return fil.extension(filepath).lower()


def _is_m4a(filepath: str) -> bool:
    return _audio_format(filepath) in ("m4a", "aac")


def _is_mp3(filepath: str) -> bool:
    return _audio_format(filepath) == "mp3"


def _is_vorbis(filepath: str) -> bool:
    return _audio_format(filepath) in _VORBIS_COMMENT_FORMATS


# ---------------------------------------------------------------------------
# Tag reading
# ---------------------------------------------------------------------------

_M4A_TAG_MAP = {"artist": "©ART", "title": "©nam", "album": "©alb", "year": "©day", "track": "trkn", "genre": "©gen"}


def _read_tags_mp3(filepath: str) -> tuple[str | None, str | None, str | None, int | None, int | None, str | None]:
    """Read ID3 tags from an MP3 file."""
    artist = title = album = genre = None
    track = year = None
    audio = MP3(filepath)
    if audio.tags:
        artist = str(audio.tags.get("TPE1", "")).strip() or None
        title = str(audio.tags.get("TIT2", "")).strip() or None
        album = str(audio.tags.get("TALB", "")).strip() or None
        genre_tag = audio.tags.get("TCON")
        genre = str(genre_tag).strip() or None if genre_tag else None
        trk_raw = str(audio.tags.get("TRCK", "")).strip()
        if trk_raw:
            try:
                track = int(trk_raw.split("/")[0])
            except ValueError:
                pass
        yr_raw = str(audio.tags.get("TDRC", "")).strip()
        if yr_raw:
            try:
                year = int(yr_raw[:4])
            except ValueError:
                pass
    return artist, title, album, track, year, genre


def _read_tags_m4a(filepath: str) -> tuple[str | None, str | None, str | None, int | None, int | None, str | None]:
    """Read iTunes atoms from an M4A/AAC file."""
    tags = MP4(filepath).tags or {}
    artist = (tags.get(_M4A_TAG_MAP["artist"], [None])[0] or "").strip() or None
    title = (tags.get(_M4A_TAG_MAP["title"], [None])[0] or "").strip() or None
    album = (tags.get(_M4A_TAG_MAP["album"], [None])[0] or "").strip() or None
    genre = (tags.get(_M4A_TAG_MAP["genre"], [None])[0] or "").strip() or None
    track: int | None = None
    year: int | None = None
    trkn = tags.get(_M4A_TAG_MAP["track"])
    if trkn:
        try:
            track = int(trkn[0][0])
        except (ValueError, IndexError, TypeError):
            pass
    day = (tags.get(_M4A_TAG_MAP["year"], [None])[0] or "").strip()
    if day:
        try:
            year = int(day[:4])
        except ValueError:
            pass
    return artist, title, album, track, year, genre


def _read_tags_vorbis(filepath: str) -> tuple[str | None, str | None, str | None, int | None, int | None, str | None]:
    """Read Vorbis comments from OGG/OPUS/FLAC files."""
    artist = title = album = genre = None
    track = year = None
    audio = mutagen.File(filepath)
    if audio and audio.tags:
        artist = (audio.tags.get("artist", [None])[0] or "").strip() or None
        title = (audio.tags.get("title", [None])[0] or "").strip() or None
        album = (audio.tags.get("album", [None])[0] or "").strip() or None
        genre = (audio.tags.get("genre", [None])[0] or "").strip() or None
        trk_raw = (audio.tags.get("tracknumber", [None])[0] or "").strip()
        if trk_raw:
            try:
                track = int(trk_raw.split("/")[0])
            except ValueError:
                pass
        yr_raw = (audio.tags.get("date", [None])[0] or "").strip()
        if yr_raw:
            try:
                year = int(yr_raw[:4])
            except ValueError:
                pass
    return artist, title, album, track, year, genre


def _read_existing_tags(filepath: str) -> tuple[str | None, str | None, str | None, int | None, int | None, str | None]:
    """Returns (artist, title, album, track, year, genre) from existing file tags."""
    try:
        if _is_m4a(filepath):
            return _read_tags_m4a(filepath)
        if _is_vorbis(filepath):
            return _read_tags_vorbis(filepath)
        return _read_tags_mp3(filepath)
    except Exception as e:
        log.logger.warning("Could not read tags from %s: %s", filepath, str(e))
        return None, None, None, None, None, None


# ---------------------------------------------------------------------------
# Tag writing
# ---------------------------------------------------------------------------


def _write_tags(filepath: str, audio_tags: AudioTags) -> None:
    """Write tags to an audio file across all supported formats."""
    try:
        if _is_m4a(filepath):
            _write_tags_m4a(filepath, audio_tags)
        elif _is_vorbis(filepath):
            _write_tags_vorbis(filepath, audio_tags)
        else:
            _write_tags_mp3(filepath, audio_tags)
        log.logger.info(
            "Tags written: %s | artist=%s title=%s album=%s track=%s year=%s genre=%s",
            filepath, audio_tags.artist, audio_tags.title, audio_tags.album,
            audio_tags.track, audio_tags.year, audio_tags.genre,
        )
    except Exception as e:
        log.logger.error("Failed to write tags for %s: %s", filepath, str(e))


def _write_tags_mp3(filepath: str, audio_tags: AudioTags) -> None:
    try:
        id3 = ID3(filepath)
    except ID3NoHeaderError:
        id3 = ID3()
    if audio_tags.artist:
        id3["TPE1"] = TPE1(encoding=3, text=audio_tags.artist)
    if audio_tags.title:
        id3["TIT2"] = TIT2(encoding=3, text=audio_tags.title)
    if audio_tags.album:
        id3["TALB"] = TALB(encoding=3, text=audio_tags.album)
    if audio_tags.track is not None:
        id3["TRCK"] = TRCK(encoding=3, text=str(audio_tags.track))
    if audio_tags.year is not None:
        id3["TDRC"] = TDRC(encoding=3, text=str(audio_tags.year))
    if audio_tags.genre:
        id3["TCON"] = TCON(encoding=3, text=audio_tags.genre)
    if audio_tags.cover_bytes:
        id3["APIC"] = APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=audio_tags.cover_bytes)
    id3.save(filepath, v1=2, v2_version=3)


def _write_tags_m4a(filepath: str, audio_tags: AudioTags) -> None:
    audio = MP4(filepath)
    if audio.tags is None:
        audio.add_tags()
    if audio_tags.artist:
        audio.tags[_M4A_TAG_MAP["artist"]] = [audio_tags.artist]
    if audio_tags.title:
        audio.tags[_M4A_TAG_MAP["title"]] = [audio_tags.title]
    if audio_tags.album:
        audio.tags[_M4A_TAG_MAP["album"]] = [audio_tags.album]
    if audio_tags.track is not None:
        audio.tags[_M4A_TAG_MAP["track"]] = [(audio_tags.track, 0)]
    if audio_tags.year is not None:
        audio.tags[_M4A_TAG_MAP["year"]] = [str(audio_tags.year)]
    if audio_tags.genre:
        audio.tags[_M4A_TAG_MAP["genre"]] = [audio_tags.genre]
    if audio_tags.cover_bytes:
        audio.tags["covr"] = [MP4Cover(audio_tags.cover_bytes, imageformat=MP4Cover.FORMAT_JPEG)]
    audio.save()


def _write_tags_vorbis(filepath: str, audio_tags: AudioTags) -> None:
    audio = mutagen.File(filepath)
    if audio is None:
        log.logger.error("mutagen.File() returned None for %s", filepath)
        return
    if audio.tags is None:
        audio.add_tags()
    if audio_tags.artist:
        audio.tags["ARTIST"] = [audio_tags.artist]
    if audio_tags.title:
        audio.tags["TITLE"] = [audio_tags.title]
    if audio_tags.album:
        audio.tags["ALBUM"] = [audio_tags.album]
    if audio_tags.track is not None:
        audio.tags["TRACKNUMBER"] = [str(audio_tags.track)]
    if audio_tags.year is not None:
        audio.tags["DATE"] = [str(audio_tags.year)]
    if audio_tags.genre:
        audio.tags["GENRE"] = [audio_tags.genre]
    if audio_tags.cover_bytes:
        if isinstance(audio, FLAC):
            audio.clear_pictures()
            audio.add_picture(_make_flac_picture(audio_tags.cover_bytes))
        else:
            pic = _make_flac_picture(audio_tags.cover_bytes)
            encoded = base64.b64encode(pic.write()).decode("ascii")
            audio.tags["METADATA_BLOCK_PICTURE"] = [encoded]
    audio.save()


# ---------------------------------------------------------------------------
# File timestamp
# ---------------------------------------------------------------------------


def _set_file_date(filepath: str, release_date: datetime.date) -> None:
    """Sets file timestamps to the release date at 12:00:00."""
    try:
        dt = datetime.datetime(release_date.year, release_date.month, release_date.day, 12, 0, 0)
        ts = dt.timestamp()
        os.utime(filepath, (ts, ts))
        log.logger.info("Set file date of %s to %s 12:00", filepath, release_date.isoformat())
    except Exception as e:
        log.logger.error("Failed to set file date for %s: %s", filepath, str(e))


# ---------------------------------------------------------------------------
# Filename rename
# ---------------------------------------------------------------------------


def _rename_file(filepath: str, new_base: str) -> str:
    """Rename file to new_base (keeping extension). Returns new path."""
    dirpath = os.path.dirname(filepath)
    ext = os.path.splitext(filepath)[1]
    new_path = os.path.join(dirpath, new_base + ext)
    if os.path.abspath(filepath) == os.path.abspath(new_path):
        return filepath
    try:
        os.rename(filepath, new_path)
        log.logger.info("Renamed %s → %s", os.path.basename(filepath), new_base + ext)
        return new_path
    except OSError as e:
        log.logger.error("Rename failed for %s: %s", filepath, str(e))
        return filepath


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------


def _process_file(
    filepath: str,
    dir_artist: str | None,
    dir_album: str | None,
    dir_year: int | None,
    dir_date: datetime.date | None,
    dir_genre: str | None,
    mb_tracks: list[str],
    cover_bytes: bytes | None,
    dry_run: bool,
) -> str:
    """Processes a single audio file. Returns (possibly updated) filepath."""
    base, ext = os.path.splitext(os.path.basename(filepath))

    # 1. Clean filename
    clean_base = _clean_basename(base)

    # 2. Parse cleaned filename
    fn_track, fn_artist, fn_title = _parse_file_name(clean_base)

    # 3. Read existing tags
    existing_artist, existing_title, existing_album, existing_track, existing_year, existing_genre = _read_existing_tags(filepath)

    # 4. Resolve final values
    artist = existing_artist or fn_artist or dir_artist
    title = existing_title or fn_title
    album = existing_album or dir_album
    track = existing_track or fn_track
    year = existing_year or dir_year
    release_date = dir_date
    genre = existing_genre or dir_genre

    # 5. MusicBrainz track title from track list
    if not title and track is not None and mb_tracks and (track - 1) < len(mb_tracks):
        title = _sentence_case(mb_tracks[track - 1])

    # 6. MusicBrainz year/date lookup if still missing
    if year is None and artist and album:
        mb_year, mb_date, mb_genre, _, _ = _mb_lookup_release(artist, album)
        year = mb_year
        release_date = mb_date
        if not genre:
            genre = mb_genre
    if year is None and artist and title:
        year, release_date = _mb_lookup_track(artist, title)

    if year and not release_date:
        release_date = datetime.date(year, 1, 1)

    # 7. Normalise capitalisation
    if artist:
        artist = _title_case(artist)
    if title:
        title = _sentence_case(title)

    # 8. Validate genre against ID3v1 list
    if genre:
        genre = _find_genre(genre) or genre

    log.logger.info(
        "File: %s  artist=%s  title=%s  album=%s  track=%s  year=%s  genre=%s  date=%s",
        base,
        artist,
        title,
        album,
        track,
        year,
        genre,
        release_date,
    )

    if dry_run:
        return filepath

    # 9. Rename file if needed
    if clean_base != base:
        filepath = _rename_file(filepath, clean_base)

    # 10. Write tags
    _write_tags(filepath, AudioTags(artist=artist, title=title, album=album, track=track, year=year, genre=genre, cover_bytes=cover_bytes))

    # 11. Set file timestamp
    if release_date:
        _set_file_date(filepath, release_date)
    elif year:
        _set_file_date(filepath, datetime.date(year, 1, 1))

    return filepath


# ---------------------------------------------------------------------------
# Per-directory processing
# ---------------------------------------------------------------------------


def _process_directory(dirpath: str, dry_run: bool) -> None:
    """Processes all audio files in a single directory."""
    dir_name = os.path.basename(dirpath)
    dir_artist, dir_album, dir_year = _parse_dir_name(dir_name)
    log.logger.info("Directory: %s  →  artist=%s  album=%s  year=%s", dir_name, dir_artist, dir_album, dir_year)

    mb_tracks: list[str] = []
    dir_date: datetime.date | None = None
    dir_genre: str | None = None
    cover_bytes: bytes | None = None
    release_id: str | None = None

    if dir_artist and dir_album:
        mb_year, mb_date, mb_genre, mb_tracks, release_id = _mb_lookup_release(dir_artist, dir_album)
        if mb_year and dir_year is None:
            dir_year = mb_year
        if mb_date:
            dir_date = mb_date
        if mb_genre:
            dir_genre = mb_genre

    if dir_year and not dir_date:
        dir_date = datetime.date(dir_year, 1, 1)

    # Fetch cover art from MusicBrainz
    if release_id:
        cover_bytes = _fetch_cover_art(release_id)

    # Save folder cover (only if this looks like an album folder with actual cover art)
    if cover_bytes and dir_album and not dry_run:
        existing_cover = os.path.join(dirpath, _COVER_FILENAME)
        if not os.path.exists(existing_cover):
            _save_cover_to_folder(dirpath, cover_bytes)

    audio_files = sorted(
        [os.path.join(dirpath, f) for f in os.listdir(dirpath) if fil.is_audio_file(f)],
        key=lambda p: os.path.basename(p).lower(),
    )
    log.logger.info("Found %d audio file(s) in %s", len(audio_files), dirpath)

    for filepath in audio_files:
        _process_file(filepath, dir_artist, dir_album, dir_year, dir_date, dir_genre, mb_tracks, cover_bytes, dry_run)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    util.init("audio-normalize")
    parser = argparse.ArgumentParser(description="Normalize audio metadata, cover art, and filenames")
    parser.add_argument("-f", "--files", nargs="+", help="Files and/or directories to process (default: E:\\Musique)")
    parser.add_argument("--dry-run", action="store_true", help="Parse and log actions without modifying anything")
    parser.add_argument("-g", "--debug", required=False, type=int, help="Debug level")
    args = parser.parse_args()

    if args.debug:
        util.set_debug_level(args.debug)

    inputs = args.files if args.files else [r"E:\Musique"]
    dry_run = args.dry_run
    if dry_run:
        log.logger.info("DRY RUN mode — no files will be modified")

    dirs_to_process: list[str] = []
    files_by_dir: dict[str, list[str]] = {}

    for entry in inputs:
        entry = os.path.abspath(entry)
        if os.path.isdir(entry):
            dirs_to_process.append(entry)
        elif fil.is_audio_file(entry):
            parent = os.path.dirname(entry)
            files_by_dir.setdefault(parent, []).append(entry)
        else:
            log.logger.warning("Skipping %s: not a directory or audio file", entry)

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
                    _process_directory(subdir, dry_run)
                except Exception as e:
                    log.logger.error("Error processing %s: %s", subdir, str(e))
        if root_audio:
            log.logger.info("Processing %d audio file(s) directly in %s", len(root_audio), root)
            _process_directory(root, dry_run)

    for parent, file_list in sorted(files_by_dir.items()):
        dir_artist, dir_album, dir_year = _parse_dir_name(os.path.basename(parent))
        mb_tracks: list[str] = []
        dir_date: datetime.date | None = None
        dir_genre: str | None = None
        cover_bytes: bytes | None = None
        release_id: str | None = None
        if dir_artist and dir_album:
            mb_year, dir_date, dir_genre, mb_tracks, release_id = _mb_lookup_release(dir_artist, dir_album)
            if mb_year and dir_year is None:
                dir_year = mb_year
        if dir_year and not dir_date:
            dir_date = datetime.date(dir_year, 1, 1)
        if release_id:
            cover_bytes = _fetch_cover_art(release_id)
        log.logger.info("Processing %d file(s) from %s", len(file_list), parent)
        for filepath in sorted(file_list):
            try:
                _process_file(filepath, dir_artist, dir_album, dir_year, dir_date, dir_genre, mb_tracks, cover_bytes, dry_run)
            except Exception as e:
                log.logger.error("Error processing %s: %s", filepath, str(e))

    log.logger.info("Done.")
    sys.exit(0)


if __name__ == "__main__":
    main()
