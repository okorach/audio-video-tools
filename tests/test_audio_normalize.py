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

"""Tests for mediatools.audio_normalize"""

import datetime as dt
import pathlib
import os
import shutil
from unittest.mock import MagicMock, patch

import pytest
from mutagen.id3 import ID3

from mediatools import tools
import mediatools.audio_normalize as norm
from pathlib import Path

FIXTURE_MP3 = os.path.join("it", "seal.mp3")


# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


def test_find_genre_exact() -> None:
    """Find genre exact"""
    assert norm.find_genre("Rock") == "Rock"
    assert norm.find_genre("rock") == "Rock"
    assert norm.find_genre("BLUES") == "Blues"


def test_find_genre_fuzzy() -> None:
    """Find genre fuzzy"""
    assert norm.find_genre("Jazz") == "Jazz"
    assert norm.find_genre("Classic") == "Classic Rock"


def test_find_genre_unknown() -> None:
    """Find genre unknown"""
    assert norm.find_genre("XYZ_NotAGenre_12345") is None
    assert norm.find_genre("") is None
    assert norm.find_genre(None) is None


def test_find_genre_winamp() -> None:
    """Find genre winamp"""
    assert norm.find_genre("Folk") == "Folk"
    assert norm.find_genre("Synthpop") == "Synthpop"
    assert norm.find_genre("Indie") == "Indie"


def test_strip_encoding_postfix() -> None:
    """Strip encoding postfix"""
    assert norm.strip_encoding_postfix("Song (128kbit_AAC)") == "Song"
    assert norm.strip_encoding_postfix("Track [320kbps MP3]") == "Track"
    assert norm.strip_encoding_postfix("Normal Title") == "Normal Title"
    assert norm.strip_encoding_postfix("Song (256kb)") == "Song"


def test_strip_exotic_unicode() -> None:
    """Strip exotic unicode"""
    assert norm.strip_exotic_unicode("Café") == "Cafe"
    assert norm.strip_exotic_unicode("Björk") == "Bjork"
    assert norm.strip_exotic_unicode("Normal") == "Normal"
    assert norm.strip_exotic_unicode("über") == "uber"


def test_clean_basename() -> None:
    """Clean basename"""
    assert norm.clean_basename("Song (128kbit_AAC)") == "Song"
    assert norm.clean_basename("Café (320kbps MP3)") == "Cafe"
    assert norm.clean_basename("Normal Title") == "Normal Title"


def test_title_case() -> None:
    """Title case"""
    assert norm.title_case("hello world") == "Hello World"
    assert norm.title_case("") == ""
    assert norm.title_case("the BEATLES") == "The Beatles"


def test_sentence_case() -> None:
    """Sentence case"""
    assert norm.sentence_case("HELLO WORLD") == "Hello world"
    assert norm.sentence_case("") == ""
    assert norm.sentence_case("come together") == "Come together"


def test_parse_dir_name_artist_album_year() -> None:
    """Parse dir name artist album year"""
    artist, album, year = norm.parse_dir_name("The Beatles - Abbey Road (1969)")
    assert artist == "The Beatles"
    assert album == "Abbey Road"
    assert year == 1969


def test_parse_dir_name_artist_album_no_year() -> None:
    """Parse dir name artist album no year"""
    artist, album, year = norm.parse_dir_name("Pink Floyd - The Wall")
    assert artist == "Pink Floyd"
    assert album == "The Wall"
    assert year is None


def test_parse_dir_name_artist_only() -> None:
    """Parse dir name artist only"""
    artist, album, year = norm.parse_dir_name("Radiohead")
    assert artist == "Radiohead"
    assert album is None
    assert year is None


def test_parse_file_name_track_artist_title() -> None:
    """Parse file name track artist title"""
    track, artist, title = norm.parse_file_name("01 - The Beatles - Come Together")
    assert track == 1
    assert artist == "The Beatles"
    assert title == "Come together"


def test_parse_file_name_track_title() -> None:
    """Parse file name track title"""
    track, artist, title = norm.parse_file_name("03. Blackbird")
    assert track == 3
    assert artist is None
    assert title == "Blackbird"


def test_parse_file_name_no_track() -> None:
    """Parse file name no track"""
    track, artist, title = norm.parse_file_name("Artist - Song Title")
    assert track is None
    assert artist == "Artist"
    assert title == "Song title"


def test_parse_file_name_track_only() -> None:
    """Parse file name track only"""
    track, artist, title = norm.parse_file_name("01")
    assert track == 1
    assert title is None


def test_parse_mb_date_full() -> None:
    """Parse mb date full"""
    year, date = norm.parse_mb_date("1969-09-26")
    assert year == 1969
    assert date == dt.date(1969, 9, 26)


def test_parse_mb_date_year_month() -> None:
    """Parse mb date year month"""
    year, date = norm.parse_mb_date("1973-03")
    assert year == 1973
    assert date == dt.date(1973, 3, 1)


def test_parse_mb_date_year_only() -> None:
    """Parse mb date year only"""
    year, date = norm.parse_mb_date("1994")
    assert year == 1994
    assert date == dt.date(1994, 1, 1)


def test_parse_mb_date_empty() -> None:
    """Parse mb date empty"""
    year, date = norm.parse_mb_date("")
    assert year is None
    assert date is None


def test_parse_mb_date_invalid() -> None:
    """Parse mb date invalid"""
    year, date = norm.parse_mb_date("not-a-date")
    assert year is None


# ---------------------------------------------------------------------------
# MusicBrainz mock tests
# ---------------------------------------------------------------------------


def _mb_release_result(date: str = "1994-10-03", genre: str = "Rock") -> dict:
    """Returns the result of a MusicBrainz search of releases, with a release of a date"""
    return {
        "release-list": [
            {
                "id": "release-id-123",
                "date": date,
            }
        ]
    }


def _mb_full_release(date: str = "1994-10-03", genre: str = "Rock") -> dict:
    """Returns the result of a MusicBrainz search of a release with its date and its genre"""
    return {
        "release": {
            "date": date,
            "genre-list": [{"name": genre}],
            "tag-list": [],
            "medium-list": [
                {
                    "track-list": [
                        {"recording": {"title": "Track One"}},
                        {"recording": {"title": "Track Two"}},
                    ]
                }
            ],
        }
    }


def test_extract_genre_from_genre_list() -> None:
    """Extract genre from genre list"""
    release = {"genre-list": [{"name": "Rock"}, {"name": "Pop"}], "tag-list": []}
    assert norm.extract_genre_from_release(release) == "Rock"


def test_extract_genre_from_tag_list_fallback() -> None:
    """Extract genre from tag list fallback"""
    release = {"genre-list": [], "tag-list": [{"name": "Jazz"}, {"name": "Other"}]}
    assert norm.extract_genre_from_release(release) == "Jazz"


def test_extract_genre_none_when_unknown() -> None:
    """Extract genre none when unknown"""
    release = {"genre-list": [{"name": "NotAGenre12345"}], "tag-list": [{"name": "AlsoNotAGenre"}]}
    assert norm.extract_genre_from_release(release) is None


def test_extract_genre_empty_release() -> None:
    """Extract genre empty release"""
    assert norm.extract_genre_from_release({}) is None


def test_extract_tracks_from_release() -> None:
    """Extract tracks from release"""
    release = {
        "medium-list": [
            {"track-list": [{"recording": {"title": "Song A"}}, {"recording": {"title": "Song B"}}]},
            {"track-list": [{"recording": {"title": "Song C"}}]},
        ]
    }
    tracks = norm.extract_tracks_from_release(release)
    assert tracks == ["Song A", "Song B", "Song C"]


def test_extract_tracks_empty() -> None:
    """Extract tracks empty"""
    assert not norm.extract_tracks_from_release({})


@patch("mediatools.audio_normalize.musicbrainzngs.get_release_by_id")
@patch("mediatools.audio_normalize.musicbrainzngs.search_releases")
def test_mb_lookup_release_success(mock_search: MagicMock, mock_get: MagicMock) -> None:
    """Mb lookup release success"""
    mock_search.return_value = _mb_release_result()
    mock_get.return_value = _mb_full_release()
    year, date, genre, tracks, release_id = norm.mb_lookup_release("Seal", "Seal")
    assert year == 1994
    assert date == dt.date(1994, 10, 3)
    assert genre == "Rock"
    assert tracks == ["Track One", "Track Two"]
    assert release_id == "release-id-123"


@patch("mediatools.audio_normalize.musicbrainzngs.search_releases")
def test_mb_lookup_release_no_results(mock_search: MagicMock) -> None:
    """Mb lookup release no results"""
    mock_search.return_value = {"release-list": []}
    year, date, genre, tracks, release_id = norm.mb_lookup_release("Unknown", "Unknown")
    assert year is None
    assert not tracks
    assert release_id is None


@patch("mediatools.audio_normalize.musicbrainzngs.search_releases")
def test_mb_lookup_release_empty_artist(mock_search: MagicMock) -> None:
    """Mb lookup release empty artist"""
    year, date, genre, tracks, release_id = norm.mb_lookup_release("", "Album")
    mock_search.assert_not_called()
    assert year is None


@patch("mediatools.audio_normalize.musicbrainzngs.search_releases")
def test_mb_lookup_release_exception(mock_search: MagicMock) -> None:
    """Mb lookup release exception"""
    mock_search.side_effect = Exception("Network error")
    year, date, genre, tracks, release_id = norm.mb_lookup_release("Artist", "Album")
    assert year is None
    assert not tracks


@patch("mediatools.audio_normalize.musicbrainzngs.search_recordings")
def test_mb_lookup_track_success(mock_search: MagicMock) -> None:
    """Mb lookup track success"""
    mock_search.return_value = {"recording-list": [{"release-list": [{"date": "1994-10-03"}]}]}
    year, date = norm.mb_lookup_track("Seal", "Crazy")
    assert year == 1994
    assert date == dt.date(1994, 10, 3)


@patch("mediatools.audio_normalize.musicbrainzngs.search_recordings")
def test_mb_lookup_track_no_date(mock_search: MagicMock) -> None:
    """Mb lookup track no date"""
    mock_search.return_value = {"recording-list": [{"release-list": [{"date": ""}]}]}
    year, date = norm.mb_lookup_track("Seal", "Crazy")
    assert year is None


@patch("mediatools.audio_normalize.musicbrainzngs.search_recordings")
def test_mb_lookup_track_empty(mock_search: MagicMock) -> None:
    """Mb lookup track empty"""
    year, date = norm.mb_lookup_track("", "")
    mock_search.assert_not_called()
    assert year is None


@patch("mediatools.audio_normalize.musicbrainzngs.search_recordings")
def test_mb_lookup_track_exception(mock_search: MagicMock) -> None:
    """Mb lookup track exception"""
    mock_search.side_effect = Exception("error")
    year, date = norm.mb_lookup_track("Artist", "Title")
    assert year is None


# ---------------------------------------------------------------------------
# Cover art tests
# ---------------------------------------------------------------------------


@patch("mediatools.audio_normalize.musicbrainzngs.get_image_front")
def test_fetch_cover_art_success(mock_get: MagicMock) -> None:
    """Fetch cover art success"""
    mock_get.return_value = b"JPEG_DATA"
    data = norm.fetch_cover_art("release-123")
    assert data == b"JPEG_DATA"


@patch("mediatools.audio_normalize.musicbrainzngs.get_image_front")
def test_fetch_cover_art_exception(mock_get: MagicMock) -> None:
    """Fetch cover art exception"""
    mock_get.side_effect = Exception("Not found")
    data = norm.fetch_cover_art("release-123")
    assert data is None


def test_fetch_cover_art_no_id() -> None:
    """Fetch cover art no id"""
    data = norm.fetch_cover_art("")
    assert data is None


def test_resize_image_no_pillow() -> None:
    """Resize image no pillow"""
    original = b"FAKE_IMAGE"
    with patch.object(norm, "_PIL_AVAILABLE", False):
        result = norm.resize_image(original)
    assert result == original


def test_save_cover_to_folder(tmp_path: Path) -> None:
    """Save cover to folder"""
    fake_image = b"FAKE_IMAGE_DATA"
    with patch("mediatools.audio_normalize.resize_image", return_value=fake_image):
        norm.save_cover_to_folder(str(tmp_path), fake_image)
    assert os.path.exists(tmp_path / "folder.jpg")


def test_save_cover_to_folder_error(tmp_path: Path) -> None:
    """Save cover to folder error"""
    with patch("mediatools.audio_normalize.resize_image", side_effect=Exception("err")):
        norm.save_cover_to_folder(str(tmp_path), b"data")


# ---------------------------------------------------------------------------
# Tag read/write tests (using real MP3 fixture)
# ---------------------------------------------------------------------------


def test_read_existing_tags_mp3(tmp_path: Path) -> None:
    """Read existing tags mp3"""
    dest = str(tmp_path / "seal.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    artist, title, album, track, year, genre = norm.read_existing_tags(dest)
    assert True  # just check it doesn't crash


def test_read_existing_tags_missing_file() -> None:
    """Read existing tags missing file"""
    artist, title, album, track, year, genre = norm.read_existing_tags("/nonexistent/file.mp3")
    assert artist is None
    assert title is None


def test_read_existing_tags_m4a() -> None:
    """Read existing tags m4a"""
    mock_mp4 = MagicMock()
    mock_mp4.tags = {
        "©ART": ["Test Artist"],
        "©nam": ["Test Title"],
        "©alb": ["Test Album"],
        "trkn": [(2, 0)],
        "©day": ["2001"],
        "©gen": ["Rock"],
    }
    with patch("mediatools.audio_normalize.MP4", return_value=mock_mp4):
        artist, title, album, track, year, genre = norm.read_existing_tags("song.m4a")
    assert artist == "Test Artist"
    assert title == "Test Title"
    assert album == "Test Album"
    assert track == 2
    assert year == 2001
    assert genre == "Rock"


def test_read_existing_tags_m4a_no_tags() -> None:
    """Read existing tags m4a no tags"""
    mock_mp4 = MagicMock()
    mock_mp4.tags = {}
    with patch("mediatools.audio_normalize.MP4", return_value=mock_mp4):
        artist, title, album, track, year, genre = norm.read_existing_tags("song.m4a")
    assert artist is None


def test_read_existing_tags_vorbis() -> None:
    """Read existing tags vorbis"""
    mock_audio = MagicMock()
    mock_audio.tags = {
        "artist": ["Seal"],
        "title": ["Crazy"],
        "album": ["Seal"],
        "tracknumber": ["01"],
        "date": ["1994"],
        "genre": ["Rock"],
    }
    with patch("mediatools.audio_normalize.mutagen.File", return_value=mock_audio):
        artist, title, album, track, year, genre = norm.read_existing_tags("song.ogg")
    assert artist == "Seal"
    assert title == "Crazy"
    assert track == 1
    assert year == 1994
    assert genre == "Rock"


def test_read_existing_tags_vorbis_no_tags() -> None:
    """Read existing tags vorbis no tags"""
    mock_audio = MagicMock()
    mock_audio.tags = None
    with patch("mediatools.audio_normalize.mutagen.File", return_value=mock_audio):
        artist, title, album, track, year, genre = norm.read_existing_tags("song.flac")
    assert artist is None
    assert title is None


def test_read_existing_tags_vorbis_tracknumber_with_total() -> None:
    """Read existing tags vorbis tracknumber with total"""
    mock_audio = MagicMock()
    mock_audio.tags = {"tracknumber": ["3/12"], "date": ["2005-06"]}
    with patch("mediatools.audio_normalize.mutagen.File", return_value=mock_audio):
        artist, title, album, track, year, genre = norm.read_existing_tags("song.opus")
    assert track == 3
    assert year == 2005


def test_write_tags_mp3(tmp_path: Path) -> None:
    """Write tags mp3"""
    dest = str(tmp_path / "seal.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    norm.write_tags(dest, norm.AudioTags(artist="Seal", title="Crazy", album="Seal", track=1, year=1994, genre="Rock"))
    tags = ID3(dest)
    assert str(tags["TPE1"]) == "Seal"
    assert str(tags["TIT2"]) == "Crazy"
    assert str(tags["TCON"]) == "Rock"


def test_write_tags_mp3_with_cover(tmp_path: Path) -> None:
    """Write tags mp3 with cover"""
    dest = str(tmp_path / "seal.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    norm.write_tags(dest, norm.AudioTags(artist="Seal", title="Crazy", album="Seal", track=1, year=1994, genre="Rock", cover_bytes=b"\xff\xd8\xff"))
    tags = ID3(dest)
    assert any(k.startswith("APIC") for k in tags)


def test_write_tags_m4a() -> None:
    """Write tags m4a"""
    mock_mp4 = MagicMock()
    mock_mp4.tags = {}
    with patch("mediatools.audio_normalize.MP4", return_value=mock_mp4):
        norm.write_tags("song.m4a", norm.AudioTags(artist="Artist", title="Title", album="Album", track=1, year=2000, genre="Rock"))
    assert mock_mp4.save.called


def test_write_tags_m4a_with_cover() -> None:
    """Write tags m4a with cover"""
    mock_mp4 = MagicMock()
    mock_mp4.tags = {}
    with patch("mediatools.audio_normalize.MP4", return_value=mock_mp4):
        norm.write_tags(
            "song.m4a", norm.AudioTags(artist="Artist", title="Title", album="Album", track=1, year=2000, genre="Pop", cover_bytes=b"\xff\xd8\xff")
        )
    assert "covr" in mock_mp4.tags


def test_write_tags_vorbis_ogg() -> None:
    """Write tags vorbis ogg"""
    mock_audio = MagicMock()
    mock_audio.tags = {}
    mock_audio.__class__ = MagicMock  # not FLAC
    with patch("mediatools.audio_normalize.mutagen.File", return_value=mock_audio):
        norm.write_tags("song.ogg", norm.AudioTags(artist="Artist", title="Title", album="Album", track=2, year=2005, genre="Folk"))
    assert mock_audio.save.called


def test_write_tags_vorbis_none_file() -> None:
    """Write tags vorbis none file"""
    with patch("mediatools.audio_normalize.mutagen.File", return_value=None):
        norm.write_tags("song.ogg", norm.AudioTags(artist="Artist", title="Title", album="Album", track=1, year=2000))


def test_write_tags_exception(tmp_path: Path) -> None:
    """Write tags exception"""
    norm.write_tags("/nonexistent/song.mp3", norm.AudioTags(artist="Artist", title="Title", album="Album", track=1, year=2000))


# ---------------------------------------------------------------------------
# File timestamp and rename tests
# ---------------------------------------------------------------------------


def test_set_file_date(tmp_path: Path) -> None:
    """Set file date"""
    f = tmp_path / "test.mp3"
    f.write_bytes(b"data")
    norm.set_file_date(str(f), dt.date(1994, 10, 3))
    stat = os.stat(str(f))
    file_time = dt.datetime.fromtimestamp(stat.st_mtime)
    assert file_time.year == 1994
    assert file_time.month == 10
    assert file_time.day == 3


def test_set_file_date_error() -> None:
    """Set file date error"""
    norm.set_file_date("/nonexistent/file.mp3", dt.date(2000, 1, 1))


def test_rename_file(tmp_path: Path) -> None:
    """Rename file"""
    src = tmp_path / "old name.mp3"
    src.write_bytes(b"data")
    new_path = norm.rename_file(str(src), "new name")
    assert os.path.exists(new_path)
    assert "new name.mp3" in new_path


def test_rename_file_same_name(tmp_path: Path) -> None:
    """Rename file same name"""
    src = tmp_path / "same.mp3"
    src.write_bytes(b"data")
    result = norm.rename_file(str(src), "same")
    assert result == str(src)


def test_rename_file_error(tmp_path: Path) -> None:
    """Rename file error"""
    src = tmp_path / "test.mp3"
    src.write_bytes(b"data")
    with patch("mediatools.audio_normalize.os.rename", side_effect=OSError("denied")):
        result = norm.rename_file(str(src), "other")
    assert result == str(src)


# ---------------------------------------------------------------------------
# process_file integration tests
# ---------------------------------------------------------------------------


@patch("mediatools.audio_normalize.write_tags")
@patch("mediatools.audio_normalize.set_file_date")
def test_process_file_dry_run(mock_date: MagicMock, mock_write: MagicMock, tmp_path: Path) -> None:
    """Process file dry run"""
    dest = str(tmp_path / "01 - Seal - Crazy.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    norm.process_file(dest, "Seal", "Seal", 1994, dt.date(1994, 10, 3), "Rock", [], None, dry_run=True)
    mock_write.assert_not_called()
    mock_date.assert_not_called()


@patch("mediatools.audio_normalize.set_file_date")
@patch("mediatools.audio_normalize.write_tags")
def test_process_file_writes_tags(mock_write: MagicMock, mock_date: MagicMock, tmp_path: Path) -> None:
    """Process file writes tags"""
    dest = str(tmp_path / "01 - Seal - Crazy.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    norm.process_file(dest, "Seal", "Seal", 1994, dt.date(1994, 10, 3), "Rock", [], None, dry_run=False)
    mock_write.assert_called_once()
    mock_date.assert_called_once()


@patch("mediatools.audio_normalize.mb_lookup_track", return_value=(1991, dt.date(1991, 1, 1)))
@patch("mediatools.audio_normalize.write_tags")
@patch("mediatools.audio_normalize.set_file_date")
def test_process_file_mb_track_lookup(mock_date: MagicMock, mock_write: MagicMock, mock_track: MagicMock, tmp_path: Path) -> None:
    """Process file mb track lookup"""
    dest = str(tmp_path / "Artist - Title.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    tags = ID3(dest)
    tags.delall("TDRC")
    tags.save(dest)
    norm.process_file(dest, None, None, None, None, None, [], None, dry_run=False)
    mock_track.assert_called()


@patch("mediatools.audio_normalize.write_tags")
@patch("mediatools.audio_normalize.set_file_date")
def test_process_file_mb_tracks_title(mock_date: MagicMock, mock_write: MagicMock, tmp_path: Path) -> None:
    """Process file mb tracks title"""
    dest = str(tmp_path / "03.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    tags = ID3(dest)
    tags.delall("TIT2")
    tags.delall("TRCK")
    tags.save(dest)
    mb_tracks = ["Track One", "Track Two", "Wild"]
    norm.process_file(dest, "Seal", "Seal", 1994, None, None, mb_tracks, None, dry_run=False)
    _, call_kwargs = mock_write.call_args
    # title comes from mb_tracks[2] (track 3 → index 2)


@patch("mediatools.audio_normalize.write_tags")
@patch("mediatools.audio_normalize.set_file_date")
def test_process_file_renames_dirty_filename(mock_date: MagicMock, mock_write: MagicMock, tmp_path: Path) -> None:
    """Process file renames dirty filename"""
    dest = str(tmp_path / "Song (128kbit_AAC).mp3")
    shutil.copy(FIXTURE_MP3, dest)
    norm.process_file(dest, "Artist", "Album", 2000, None, None, [], None, dry_run=False)
    assert os.path.exists(str(tmp_path / "Song.mp3"))


# ---------------------------------------------------------------------------
# process_directory tests
# ---------------------------------------------------------------------------


@patch("mediatools.audio_normalize.fetch_cover_art", return_value=None)
@patch("mediatools.audio_normalize.mb_lookup_release", return_value=(1994, dt.date(1994, 10, 3), "Rock", ["Crazy", "Newborn"], "rel-123"))
@patch("mediatools.audio_normalize.process_file")
def test_process_directory(mock_pf: MagicMock, mock_mb: MagicMock, mock_cover: MagicMock, tmp_path: Path) -> None:
    """Process directory"""
    shutil.copy(FIXTURE_MP3, str(tmp_path / "01 - Seal - Crazy.mp3"))
    (tmp_path / "notes.txt").write_text("ignore me")
    norm.process_directory(str(tmp_path), dry_run=False)
    mock_pf.assert_called()


@patch("mediatools.audio_normalize.fetch_cover_art", return_value=b"JPEG_DATA")
@patch("mediatools.audio_normalize.save_cover_to_folder")
@patch("mediatools.audio_normalize.mb_lookup_release", return_value=(1994, dt.date(1994, 10, 3), "Rock", [], "rel-123"))
@patch("mediatools.audio_normalize.process_file")
def test_process_directory_saves_cover(mock_pf: MagicMock, mock_mb: MagicMock, mock_save: MagicMock, mock_cover: MagicMock, tmp_path: Path) -> None:
    """Process directory saves cover"""
    album_dir = tmp_path / "Seal - Seal"
    album_dir.mkdir()
    shutil.copy(FIXTURE_MP3, str(album_dir / "01.mp3"))
    norm.process_directory(str(album_dir), dry_run=False)
    mock_save.assert_called_once()


@patch("mediatools.audio_normalize.fetch_cover_art", return_value=b"JPEG_DATA")
@patch("mediatools.audio_normalize.save_cover_to_folder")
@patch("mediatools.audio_normalize.mb_lookup_release", return_value=(1994, dt.date(1994, 10, 3), "Rock", [], "rel-123"))
@patch("mediatools.audio_normalize.process_file")
def test_process_directory_skip_cover_if_exists(
    mock_pf: MagicMock, mock_mb: MagicMock, mock_save: MagicMock, mock_cover: MagicMock, tmp_path: Path
) -> None:
    """Process directory skip cover if exists"""
    album_dir = tmp_path / "Seal - Seal"
    album_dir.mkdir()
    shutil.copy(FIXTURE_MP3, str(album_dir / "01.mp3"))
    (album_dir / "folder.jpg").write_bytes(b"existing")
    norm.process_directory(str(album_dir), dry_run=False)
    mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


@patch("mediatools.audio_normalize.process_directory")
def test_main_default_dir(mock_pd: MagicMock) -> None:
    """Main default dir"""
    with (
        patch("sys.argv", ["audiotool", "normalize"]),
        patch("os.path.isdir", return_value=True),
        patch("os.listdir", return_value=[]),
        pytest.raises(SystemExit),
    ):
        tools.audiotool()


@patch("mediatools.audio_normalize.process_directory")
def test_main_dry_run(mock_pd: MagicMock, tmp_path: Path) -> None:
    """Main dry run"""
    with (
        patch("sys.argv", ["audiotool", "normalize", "-f", str(tmp_path), "--dry-run"]),
        patch("os.listdir", return_value=[]),
        pytest.raises(SystemExit),
    ):
        tools.audiotool()


@patch("mediatools.audio_normalize.process_file")
@patch("mediatools.audio_normalize.mb_lookup_release", return_value=(None, None, None, [], None))
@patch("mediatools.audio_normalize.fetch_cover_art", return_value=None)
def test_main_with_mp3_file(mock_cover: MagicMock, mock_mb: MagicMock, mock_pf: MagicMock, tmp_path: Path) -> None:
    """Main with mp3 file"""
    dest = str(tmp_path / "seal.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    with patch("sys.argv", ["audiotool", "normalize", "-f", dest]), pytest.raises(SystemExit):
        tools.audiotool()
    mock_pf.assert_called()


def test_main_non_audio_file(tmp_path: Path) -> None:
    """Main non audio file"""
    f = str(tmp_path / "notes.txt")
    pathlib.Path(f).touch()
    with patch("sys.argv", ["audiotool", "normalize", "-f", f]), pytest.raises(SystemExit):
        tools.audiotool()


def test_main_debug_flag(tmp_path: Path) -> None:
    """Main debug flag"""
    with (
        patch("sys.argv", ["audiotool", "normalize", "-f", str(tmp_path), "-g", "2"]),
        patch("os.listdir", return_value=[]),
        pytest.raises(SystemExit),
    ):
        tools.audiotool()
