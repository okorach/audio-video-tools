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

"""Tests for mediatools.audio_normalize"""

import datetime
import os
import shutil
from unittest.mock import MagicMock, patch

import pytest
from mutagen.id3 import ID3

import mediatools.audio_normalize as norm

FIXTURE_MP3 = os.path.join("it", "seal.mp3")


# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


def test_find_genre_exact():
    assert norm._find_genre("Rock") == "Rock"
    assert norm._find_genre("rock") == "Rock"
    assert norm._find_genre("BLUES") == "Blues"


def test_find_genre_fuzzy():
    assert norm._find_genre("Jazz") == "Jazz"
    assert norm._find_genre("Classic") == "Classic Rock"


def test_find_genre_unknown():
    assert norm._find_genre("XYZ_NotAGenre_12345") is None
    assert norm._find_genre("") is None
    assert norm._find_genre(None) is None


def test_find_genre_winamp():
    assert norm._find_genre("Folk") == "Folk"
    assert norm._find_genre("Synthpop") == "Synthpop"
    assert norm._find_genre("Indie") == "Indie"


def test_strip_encoding_postfix():
    assert norm._strip_encoding_postfix("Song (128kbit_AAC)") == "Song"
    assert norm._strip_encoding_postfix("Track [320kbps MP3]") == "Track"
    assert norm._strip_encoding_postfix("Normal Title") == "Normal Title"
    assert norm._strip_encoding_postfix("Song (256kb)") == "Song"


def test_strip_exotic_unicode():
    assert norm._strip_exotic_unicode("Café") == "Cafe"
    assert norm._strip_exotic_unicode("Björk") == "Bjork"
    assert norm._strip_exotic_unicode("Normal") == "Normal"
    assert norm._strip_exotic_unicode("über") == "uber"


def test_clean_basename():
    assert norm._clean_basename("Song (128kbit_AAC)") == "Song"
    assert norm._clean_basename("Café (320kbps MP3)") == "Cafe"
    assert norm._clean_basename("Normal Title") == "Normal Title"


def test_title_case():
    assert norm._title_case("hello world") == "Hello World"
    assert norm._title_case("") == ""
    assert norm._title_case("the BEATLES") == "The Beatles"


def test_sentence_case():
    assert norm._sentence_case("HELLO WORLD") == "Hello world"
    assert norm._sentence_case("") == ""
    assert norm._sentence_case("come together") == "Come together"


def test_parse_dir_name_artist_album_year():
    artist, album, year = norm._parse_dir_name("The Beatles - Abbey Road (1969)")
    assert artist == "The Beatles"
    assert album == "Abbey Road"
    assert year == 1969


def test_parse_dir_name_artist_album_no_year():
    artist, album, year = norm._parse_dir_name("Pink Floyd - The Wall")
    assert artist == "Pink Floyd"
    assert album == "The Wall"
    assert year is None


def test_parse_dir_name_artist_only():
    artist, album, year = norm._parse_dir_name("Radiohead")
    assert artist == "Radiohead"
    assert album is None
    assert year is None


def test_parse_file_name_track_artist_title():
    track, artist, title = norm._parse_file_name("01 - The Beatles - Come Together")
    assert track == 1
    assert artist == "The Beatles"
    assert title == "Come together"


def test_parse_file_name_track_title():
    track, artist, title = norm._parse_file_name("03. Blackbird")
    assert track == 3
    assert artist is None
    assert title == "Blackbird"


def test_parse_file_name_no_track():
    track, artist, title = norm._parse_file_name("Artist - Song Title")
    assert track is None
    assert artist == "Artist"
    assert title == "Song title"


def test_parse_file_name_track_only():
    track, artist, title = norm._parse_file_name("01")
    assert track == 1
    assert title is None


def test_parse_mb_date_full():
    year, date = norm._parse_mb_date("1969-09-26")
    assert year == 1969
    assert date == datetime.date(1969, 9, 26)


def test_parse_mb_date_year_month():
    year, date = norm._parse_mb_date("1973-03")
    assert year == 1973
    assert date == datetime.date(1973, 3, 1)


def test_parse_mb_date_year_only():
    year, date = norm._parse_mb_date("1994")
    assert year == 1994
    assert date == datetime.date(1994, 1, 1)


def test_parse_mb_date_empty():
    year, date = norm._parse_mb_date("")
    assert year is None
    assert date is None


def test_parse_mb_date_invalid():
    year, date = norm._parse_mb_date("not-a-date")
    assert year is None


# ---------------------------------------------------------------------------
# MusicBrainz mock tests
# ---------------------------------------------------------------------------


def _mb_release_result(date="1994-10-03", genre="Rock"):
    return {
        "release-list": [
            {
                "id": "release-id-123",
                "date": date,
            }
        ]
    }


def _mb_full_release(date="1994-10-03", genre="Rock"):
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


def test_extract_genre_from_genre_list():
    release = {"genre-list": [{"name": "Rock"}, {"name": "Pop"}], "tag-list": []}
    assert norm._extract_genre_from_release(release) == "Rock"


def test_extract_genre_from_tag_list_fallback():
    release = {"genre-list": [], "tag-list": [{"name": "Jazz"}, {"name": "Other"}]}
    assert norm._extract_genre_from_release(release) == "Jazz"


def test_extract_genre_none_when_unknown():
    release = {"genre-list": [{"name": "NotAGenre12345"}], "tag-list": [{"name": "AlsoNotAGenre"}]}
    assert norm._extract_genre_from_release(release) is None


def test_extract_genre_empty_release():
    assert norm._extract_genre_from_release({}) is None


def test_extract_tracks_from_release():
    release = {
        "medium-list": [
            {"track-list": [{"recording": {"title": "Song A"}}, {"recording": {"title": "Song B"}}]},
            {"track-list": [{"recording": {"title": "Song C"}}]},
        ]
    }
    tracks = norm._extract_tracks_from_release(release)
    assert tracks == ["Song A", "Song B", "Song C"]


def test_extract_tracks_empty():
    assert norm._extract_tracks_from_release({}) == []


@patch("mediatools.audio_normalize.musicbrainzngs.get_release_by_id")
@patch("mediatools.audio_normalize.musicbrainzngs.search_releases")
def test_mb_lookup_release_success(mock_search, mock_get):
    mock_search.return_value = _mb_release_result()
    mock_get.return_value = _mb_full_release()
    year, date, genre, tracks, release_id = norm._mb_lookup_release("Seal", "Seal")
    assert year == 1994
    assert date == datetime.date(1994, 10, 3)
    assert genre == "Rock"
    assert tracks == ["Track One", "Track Two"]
    assert release_id == "release-id-123"


@patch("mediatools.audio_normalize.musicbrainzngs.search_releases")
def test_mb_lookup_release_no_results(mock_search):
    mock_search.return_value = {"release-list": []}
    year, date, genre, tracks, release_id = norm._mb_lookup_release("Unknown", "Unknown")
    assert year is None
    assert tracks == []
    assert release_id is None


@patch("mediatools.audio_normalize.musicbrainzngs.search_releases")
def test_mb_lookup_release_empty_artist(mock_search):
    year, date, genre, tracks, release_id = norm._mb_lookup_release("", "Album")
    mock_search.assert_not_called()
    assert year is None


@patch("mediatools.audio_normalize.musicbrainzngs.search_releases")
def test_mb_lookup_release_exception(mock_search):
    mock_search.side_effect = Exception("Network error")
    year, date, genre, tracks, release_id = norm._mb_lookup_release("Artist", "Album")
    assert year is None
    assert tracks == []


@patch("mediatools.audio_normalize.musicbrainzngs.search_recordings")
def test_mb_lookup_track_success(mock_search):
    mock_search.return_value = {
        "recording-list": [
            {"release-list": [{"date": "1994-10-03"}]}
        ]
    }
    year, date = norm._mb_lookup_track("Seal", "Crazy")
    assert year == 1994
    assert date == datetime.date(1994, 10, 3)


@patch("mediatools.audio_normalize.musicbrainzngs.search_recordings")
def test_mb_lookup_track_no_date(mock_search):
    mock_search.return_value = {"recording-list": [{"release-list": [{"date": ""}]}]}
    year, date = norm._mb_lookup_track("Seal", "Crazy")
    assert year is None


@patch("mediatools.audio_normalize.musicbrainzngs.search_recordings")
def test_mb_lookup_track_empty(mock_search):
    year, date = norm._mb_lookup_track("", "")
    mock_search.assert_not_called()
    assert year is None


@patch("mediatools.audio_normalize.musicbrainzngs.search_recordings")
def test_mb_lookup_track_exception(mock_search):
    mock_search.side_effect = Exception("error")
    year, date = norm._mb_lookup_track("Artist", "Title")
    assert year is None


# ---------------------------------------------------------------------------
# Cover art tests
# ---------------------------------------------------------------------------


@patch("mediatools.audio_normalize.musicbrainzngs.get_image_front")
def test_fetch_cover_art_success(mock_get):
    mock_get.return_value = b"JPEG_DATA"
    data = norm._fetch_cover_art("release-123")
    assert data == b"JPEG_DATA"


@patch("mediatools.audio_normalize.musicbrainzngs.get_image_front")
def test_fetch_cover_art_exception(mock_get):
    mock_get.side_effect = Exception("Not found")
    data = norm._fetch_cover_art("release-123")
    assert data is None


def test_fetch_cover_art_no_id():
    data = norm._fetch_cover_art("")
    assert data is None


def test_resize_image_no_pillow():
    original = b"FAKE_IMAGE"
    with patch.object(norm, "_PIL_AVAILABLE", False):
        result = norm._resize_image(original)
    assert result == original


def test_save_cover_to_folder(tmp_path):
    fake_image = b"FAKE_IMAGE_DATA"
    with patch("mediatools.audio_normalize._resize_image", return_value=fake_image):
        norm._save_cover_to_folder(str(tmp_path), fake_image)
    assert os.path.exists(tmp_path / "folder.jpg")


def test_save_cover_to_folder_error(tmp_path):
    with patch("mediatools.audio_normalize._resize_image", side_effect=Exception("err")):
        norm._save_cover_to_folder(str(tmp_path), b"data")


# ---------------------------------------------------------------------------
# Tag read/write tests (using real MP3 fixture)
# ---------------------------------------------------------------------------


def test_read_existing_tags_mp3(tmp_path):
    dest = str(tmp_path / "seal.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    artist, title, album, track, year, genre = norm._read_existing_tags(dest)
    assert True  # just check it doesn't crash


def test_read_existing_tags_missing_file():
    artist, title, album, track, year, genre = norm._read_existing_tags("/nonexistent/file.mp3")
    assert artist is None
    assert title is None


def test_read_existing_tags_m4a():
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
        artist, title, album, track, year, genre = norm._read_existing_tags("song.m4a")
    assert artist == "Test Artist"
    assert title == "Test Title"
    assert album == "Test Album"
    assert track == 2
    assert year == 2001
    assert genre == "Rock"


def test_read_existing_tags_m4a_no_tags():
    mock_mp4 = MagicMock()
    mock_mp4.tags = {}
    with patch("mediatools.audio_normalize.MP4", return_value=mock_mp4):
        artist, title, album, track, year, genre = norm._read_existing_tags("song.m4a")
    assert artist is None


def test_read_existing_tags_vorbis():
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
        artist, title, album, track, year, genre = norm._read_existing_tags("song.ogg")
    assert artist == "Seal"
    assert title == "Crazy"
    assert track == 1
    assert year == 1994
    assert genre == "Rock"


def test_read_existing_tags_vorbis_no_tags():
    mock_audio = MagicMock()
    mock_audio.tags = None
    with patch("mediatools.audio_normalize.mutagen.File", return_value=mock_audio):
        artist, title, album, track, year, genre = norm._read_existing_tags("song.flac")
    assert artist is None
    assert title is None


def test_read_existing_tags_vorbis_tracknumber_with_total():
    mock_audio = MagicMock()
    mock_audio.tags = {"tracknumber": ["3/12"], "date": ["2005-06"]}
    with patch("mediatools.audio_normalize.mutagen.File", return_value=mock_audio):
        artist, title, album, track, year, genre = norm._read_existing_tags("song.opus")
    assert track == 3
    assert year == 2005


def test_write_tags_mp3(tmp_path):
    dest = str(tmp_path / "seal.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    norm._write_tags(dest, norm.AudioTags(artist="Seal", title="Crazy", album="Seal", track=1, year=1994, genre="Rock"))
    tags = ID3(dest)
    assert str(tags["TPE1"]) == "Seal"
    assert str(tags["TIT2"]) == "Crazy"
    assert str(tags["TCON"]) == "Rock"


def test_write_tags_mp3_with_cover(tmp_path):
    dest = str(tmp_path / "seal.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    norm._write_tags(dest, norm.AudioTags(artist="Seal", title="Crazy", album="Seal", track=1, year=1994, genre="Rock", cover_bytes=b"\xff\xd8\xff"))
    tags = ID3(dest)
    assert any(k.startswith("APIC") for k in tags)


def test_write_tags_m4a():
    mock_mp4 = MagicMock()
    mock_mp4.tags = {}
    with patch("mediatools.audio_normalize.MP4", return_value=mock_mp4):
        norm._write_tags("song.m4a", norm.AudioTags(artist="Artist", title="Title", album="Album", track=1, year=2000, genre="Rock"))
    assert mock_mp4.save.called


def test_write_tags_m4a_with_cover():
    mock_mp4 = MagicMock()
    mock_mp4.tags = {}
    with patch("mediatools.audio_normalize.MP4", return_value=mock_mp4):
        norm._write_tags(
            "song.m4a", norm.AudioTags(artist="Artist", title="Title", album="Album", track=1, year=2000, genre="Pop", cover_bytes=b"\xff\xd8\xff")
        )
    assert "covr" in mock_mp4.tags


def test_write_tags_vorbis_ogg():
    mock_audio = MagicMock()
    mock_audio.tags = {}
    mock_audio.__class__ = MagicMock  # not FLAC
    with patch("mediatools.audio_normalize.mutagen.File", return_value=mock_audio):
        norm._write_tags("song.ogg", norm.AudioTags(artist="Artist", title="Title", album="Album", track=2, year=2005, genre="Folk"))
    assert mock_audio.save.called


def test_write_tags_vorbis_none_file():
    with patch("mediatools.audio_normalize.mutagen.File", return_value=None):
        norm._write_tags("song.ogg", norm.AudioTags(artist="Artist", title="Title", album="Album", track=1, year=2000))


def test_write_tags_exception(tmp_path):
    norm._write_tags("/nonexistent/song.mp3", norm.AudioTags(artist="Artist", title="Title", album="Album", track=1, year=2000))


# ---------------------------------------------------------------------------
# File timestamp and rename tests
# ---------------------------------------------------------------------------


def test_set_file_date(tmp_path):
    f = tmp_path / "test.mp3"
    f.write_bytes(b"data")
    norm._set_file_date(str(f), datetime.date(1994, 10, 3))
    stat = os.stat(str(f))
    dt = datetime.datetime.fromtimestamp(stat.st_mtime)
    assert dt.year == 1994
    assert dt.month == 10
    assert dt.day == 3


def test_set_file_date_error():
    norm._set_file_date("/nonexistent/file.mp3", datetime.date(2000, 1, 1))


def test_rename_file(tmp_path):
    src = tmp_path / "old name.mp3"
    src.write_bytes(b"data")
    new_path = norm._rename_file(str(src), "new name")
    assert os.path.exists(new_path)
    assert "new name.mp3" in new_path


def test_rename_file_same_name(tmp_path):
    src = tmp_path / "same.mp3"
    src.write_bytes(b"data")
    result = norm._rename_file(str(src), "same")
    assert result == str(src)


def test_rename_file_error(tmp_path):
    src = tmp_path / "test.mp3"
    src.write_bytes(b"data")
    with patch("mediatools.audio_normalize.os.rename", side_effect=OSError("denied")):
        result = norm._rename_file(str(src), "other")
    assert result == str(src)


# ---------------------------------------------------------------------------
# _process_file integration tests
# ---------------------------------------------------------------------------


@patch("mediatools.audio_normalize._write_tags")
@patch("mediatools.audio_normalize._set_file_date")
def test_process_file_dry_run(mock_date, mock_write, tmp_path):
    dest = str(tmp_path / "01 - Seal - Crazy.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    norm._process_file(dest, "Seal", "Seal", 1994, datetime.date(1994, 10, 3), "Rock", [], None, dry_run=True)
    mock_write.assert_not_called()
    mock_date.assert_not_called()


@patch("mediatools.audio_normalize._set_file_date")
@patch("mediatools.audio_normalize._write_tags")
def test_process_file_writes_tags(mock_write, mock_date, tmp_path):
    dest = str(tmp_path / "01 - Seal - Crazy.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    norm._process_file(dest, "Seal", "Seal", 1994, datetime.date(1994, 10, 3), "Rock", [], None, dry_run=False)
    mock_write.assert_called_once()
    mock_date.assert_called_once()


@patch("mediatools.audio_normalize._mb_lookup_track", return_value=(1991, datetime.date(1991, 1, 1)))
@patch("mediatools.audio_normalize._write_tags")
@patch("mediatools.audio_normalize._set_file_date")
def test_process_file_mb_track_lookup(mock_date, mock_write, mock_track, tmp_path):
    dest = str(tmp_path / "Artist - Title.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    tags = ID3(dest)
    tags.delall("TDRC")
    tags.save(dest)
    norm._process_file(dest, None, None, None, None, None, [], None, dry_run=False)
    mock_track.assert_called()


@patch("mediatools.audio_normalize._write_tags")
@patch("mediatools.audio_normalize._set_file_date")
def test_process_file_mb_tracks_title(mock_date, mock_write, tmp_path):
    dest = str(tmp_path / "03.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    tags = ID3(dest)
    tags.delall("TIT2")
    tags.delall("TRCK")
    tags.save(dest)
    mb_tracks = ["Track One", "Track Two", "Wild"]
    norm._process_file(dest, "Seal", "Seal", 1994, None, None, mb_tracks, None, dry_run=False)
    _, call_kwargs = mock_write.call_args
    # title comes from mb_tracks[2] (track 3 → index 2)


@patch("mediatools.audio_normalize._write_tags")
@patch("mediatools.audio_normalize._set_file_date")
def test_process_file_renames_dirty_filename(mock_date, mock_write, tmp_path):
    dest = str(tmp_path / "Song (128kbit_AAC).mp3")
    shutil.copy(FIXTURE_MP3, dest)
    norm._process_file(dest, "Artist", "Album", 2000, None, None, [], None, dry_run=False)
    assert os.path.exists(str(tmp_path / "Song.mp3"))


# ---------------------------------------------------------------------------
# _process_directory tests
# ---------------------------------------------------------------------------


@patch("mediatools.audio_normalize._fetch_cover_art", return_value=None)
@patch("mediatools.audio_normalize._mb_lookup_release", return_value=(1994, datetime.date(1994, 10, 3), "Rock", ["Crazy", "Newborn"], "rel-123"))
@patch("mediatools.audio_normalize._process_file")
def test_process_directory(mock_pf, mock_mb, mock_cover, tmp_path):
    shutil.copy(FIXTURE_MP3, str(tmp_path / "01 - Seal - Crazy.mp3"))
    (tmp_path / "notes.txt").write_text("ignore me")
    norm._process_directory(str(tmp_path), dry_run=False)
    mock_pf.assert_called()


@patch("mediatools.audio_normalize._fetch_cover_art", return_value=b"JPEG_DATA")
@patch("mediatools.audio_normalize._save_cover_to_folder")
@patch("mediatools.audio_normalize._mb_lookup_release", return_value=(1994, datetime.date(1994, 10, 3), "Rock", [], "rel-123"))
@patch("mediatools.audio_normalize._process_file")
def test_process_directory_saves_cover(mock_pf, mock_mb, mock_save, mock_cover, tmp_path):
    album_dir = tmp_path / "Seal - Seal"
    album_dir.mkdir()
    shutil.copy(FIXTURE_MP3, str(album_dir / "01.mp3"))
    norm._process_directory(str(album_dir), dry_run=False)
    mock_save.assert_called_once()


@patch("mediatools.audio_normalize._fetch_cover_art", return_value=b"JPEG_DATA")
@patch("mediatools.audio_normalize._save_cover_to_folder")
@patch("mediatools.audio_normalize._mb_lookup_release", return_value=(1994, datetime.date(1994, 10, 3), "Rock", [], "rel-123"))
@patch("mediatools.audio_normalize._process_file")
def test_process_directory_skip_cover_if_exists(mock_pf, mock_mb, mock_save, mock_cover, tmp_path):
    album_dir = tmp_path / "Seal - Seal"
    album_dir.mkdir()
    shutil.copy(FIXTURE_MP3, str(album_dir / "01.mp3"))
    (album_dir / "folder.jpg").write_bytes(b"existing")
    norm._process_directory(str(album_dir), dry_run=False)
    mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


@patch("mediatools.audio_normalize._process_directory")
def test_main_default_dir(mock_pd):
    with (
        patch("sys.argv", ["audio-normalize"]),
        patch("os.path.isdir", return_value=True),
        patch("os.listdir", return_value=[]),
        pytest.raises(SystemExit),
    ):
        norm.main()


@patch("mediatools.audio_normalize._process_directory")
def test_main_dry_run(mock_pd, tmp_path):
    with patch("sys.argv", ["audio-normalize", "-f", str(tmp_path), "--dry-run"]), patch("os.listdir", return_value=[]), pytest.raises(SystemExit):
        norm.main()


@patch("mediatools.audio_normalize._process_file")
@patch("mediatools.audio_normalize._mb_lookup_release", return_value=(None, None, None, [], None))
@patch("mediatools.audio_normalize._fetch_cover_art", return_value=None)
def test_main_with_mp3_file(mock_cover, mock_mb, mock_pf, tmp_path):
    dest = str(tmp_path / "seal.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    with patch("sys.argv", ["audio-normalize", "-f", dest]), pytest.raises(SystemExit):
        norm.main()
    mock_pf.assert_called()


def test_main_non_audio_file(tmp_path):
    f = str(tmp_path / "notes.txt")
    open(f, "w").close()
    with patch("sys.argv", ["audio-normalize", "-f", f]), pytest.raises(SystemExit):
        norm.main()


def test_main_debug_flag(tmp_path):
    with patch("sys.argv", ["audio-normalize", "-f", str(tmp_path), "-g", "2"]), patch("os.listdir", return_value=[]), pytest.raises(SystemExit):
        norm.main()
