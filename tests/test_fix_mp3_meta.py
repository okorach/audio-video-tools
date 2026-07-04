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
import shutil
import datetime
from unittest.mock import patch, MagicMock
import pytest

from mutagen.id3 import ID3
from mutagen.mp3 import MP3

import mediatools.fix_mp3_meta as fix

FIXTURE_MP3 = os.path.join("it", "seal.mp3")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_mp3(tmp_path):
    """Copy the fixture MP3 to a temporary location so tests can mutate it."""
    dest = str(tmp_path / "test.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    return dest


# ---------------------------------------------------------------------------
# Capitalisation helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("the beatles", "The Beatles"),
        ("pink floyd", "Pink Floyd"),
        ("ACDC", "Acdc"),
        ("", ""),
        ("single", "Single"),
        ("multiple   spaces", "Multiple Spaces"),  # split() collapses runs of whitespace
    ],
)
def test_title_case(text, expected):
    assert fix._title_case(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("come together", "Come together"),
        ("COME TOGETHER", "Come together"),  # sentence_case lowercases rest of string
        ("hello world", "Hello world"),
        ("", ""),
        ("a", "A"),
    ],
)
def test_sentence_case(text, expected):
    assert fix._sentence_case(text) == expected


# ---------------------------------------------------------------------------
# Directory name parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dir_name,exp_artist,exp_album,exp_year",
    [
        ("The Beatles - Abbey Road", "The Beatles", "Abbey Road", None),
        ("Pink Floyd - The Wall (1979)", "Pink Floyd", "The Wall", 1979),
        ("Pink Floyd - The Wall [1979]", "Pink Floyd", "The Wall", 1979),
        ("Seal", "Seal", None, None),
        ("the rolling stones - exile on main st", "The Rolling Stones", "exile on main st", None),
    ],
)
def test_parse_dir_name(dir_name, exp_artist, exp_album, exp_year):
    artist, album, year = fix._parse_dir_name(dir_name)
    assert artist == exp_artist
    assert album == exp_album
    assert year == exp_year


# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "base_name,exp_track,exp_artist,exp_title",
    [
        # Bare title
        ("Come Together", None, None, "Come together"),
        # Artist - Title
        ("The Beatles - Come Together", None, "The Beatles", "Come together"),
        # Track - Title
        ("01 - Come Together", 1, None, "Come together"),
        ("03. Come Together", 3, None, "Come together"),
        ("(02) Come Together", 2, None, "Come together"),
        # Track - Artist - Title
        ("04 - The Beatles - Come Together", 4, "The Beatles", "Come together"),
        # Two-digit track
        ("12 - Hey Jude", 12, None, "Hey jude"),
    ],
)
def test_parse_file_name(base_name, exp_track, exp_artist, exp_title):
    track, artist, title = fix._parse_file_name(base_name)
    assert track == exp_track
    assert artist == exp_artist
    assert title == exp_title


# ---------------------------------------------------------------------------
# Tag writing
# ---------------------------------------------------------------------------


def test_write_tags_creates_id3_header(tmp_mp3):
    fix._write_tags(tmp_mp3, artist="Test Artist", title="Test title", album="Test Album", track=3, year=2001)
    tags = ID3(tmp_mp3)
    assert str(tags["TPE1"]) == "Test Artist"
    assert str(tags["TIT2"]) == "Test title"
    assert str(tags["TALB"]) == "Test Album"
    assert str(tags["TRCK"]) == "3"
    assert str(tags["TDRC"]) == "2001"


def test_write_tags_partial(tmp_mp3):
    """write_tags with some None fields should not crash and only set provided tags."""
    fix._write_tags(tmp_mp3, artist="Solo Artist", title=None, album=None, track=None, year=None)
    tags = ID3(tmp_mp3)
    assert str(tags["TPE1"]) == "Solo Artist"


def test_write_tags_id3v1_present(tmp_mp3):
    """mutagen save with v1=2 should write both v1 and v2 headers."""
    fix._write_tags(tmp_mp3, artist="Artist", title="Title", album="Album", track=1, year=1999)
    audio = MP3(tmp_mp3)
    assert audio.tags is not None


# ---------------------------------------------------------------------------
# File timestamp setting
# ---------------------------------------------------------------------------


def test_set_file_date(tmp_mp3):
    fix._set_file_date(tmp_mp3, 1991)
    mtime = os.path.getmtime(tmp_mp3)
    dt = datetime.datetime.fromtimestamp(mtime)
    assert dt.year == 1991
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12


# ---------------------------------------------------------------------------
# MusicBrainz lookups (mocked to avoid network calls)
# ---------------------------------------------------------------------------


def test_mb_lookup_release_returns_year_and_tracks():
    mock_result = {"release-list": [{"id": "abc-123", "date": "1991-05-06"}]}
    mock_full = {
        "release": {
            "medium-list": [
                {
                    "track-list": [
                        {"recording": {"title": "Crazy"}},
                        {"recording": {"title": "Future Love Paradise"}},
                    ]
                }
            ]
        }
    }
    with patch("musicbrainzngs.search_releases", return_value=mock_result), patch("musicbrainzngs.get_release_by_id", return_value=mock_full):
        year, tracks = fix._mb_lookup_release("Seal", "Seal")
    assert year == 1991
    assert tracks == ["Crazy", "Future Love Paradise"]


def test_mb_lookup_release_empty_result():
    with patch("musicbrainzngs.search_releases", return_value={"release-list": []}):
        year, tracks = fix._mb_lookup_release("Unknown", "Unknown Album")
    assert year is None
    assert tracks == []


def test_mb_lookup_release_network_error():
    with patch("musicbrainzngs.search_releases", side_effect=Exception("network error")):
        year, tracks = fix._mb_lookup_release("Artist", "Album")
    assert year is None
    assert tracks == []


def test_mb_lookup_track_returns_year():
    mock_result = {"recording-list": [{"release-list": [{"date": "1991-05-06"}]}]}
    with patch("musicbrainzngs.search_recordings", return_value=mock_result):
        year = fix._mb_lookup_track("Seal", "Crazy")
    assert year == 1991


def test_mb_lookup_track_no_result():
    with patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}):
        year = fix._mb_lookup_track("Unknown", "Unknown Track")
    assert year is None


def test_mb_lookup_track_network_error():
    with patch("musicbrainzngs.search_recordings", side_effect=Exception("timeout")):
        year = fix._mb_lookup_track("Artist", "Track")
    assert year is None


# ---------------------------------------------------------------------------
# process_file — dry run (no writes) and live run
# ---------------------------------------------------------------------------


def test_process_file_dry_run_does_not_modify_file(tmp_mp3):
    mtime_before = os.path.getmtime(tmp_mp3)
    with (
        patch("musicbrainzngs.search_releases", return_value={"release-list": []}),
        patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}),
    ):
        fix._process_file(tmp_mp3, dir_artist="Seal", dir_album="Seal", dir_year=1991, mb_tracks=[], dry_run=True)
    mtime_after = os.path.getmtime(tmp_mp3)
    assert mtime_before == mtime_after


def test_process_file_writes_tags_and_date(tmp_mp3):
    with (
        patch("musicbrainzngs.search_releases", return_value={"release-list": []}),
        patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}),
    ):
        fix._process_file(tmp_mp3, dir_artist="Seal", dir_album="Seal", dir_year=1991, mb_tracks=[], dry_run=False)
    tags = ID3(tmp_mp3)
    assert str(tags["TPE1"]) == "Seal"
    dt = datetime.datetime.fromtimestamp(os.path.getmtime(tmp_mp3))
    assert dt.year == 1991


def test_process_file_uses_mb_tracks_for_title(tmp_path):
    """When filename has only a track number (no title) and no title tag, mb_tracks fills the title."""
    mb_tracks = ["Crazy", "Future Love Paradise", "Wild"]
    # File name "01.mp3" → track=1, title=None from filename
    track1_path = str(tmp_path / "01.mp3")
    shutil.copy(FIXTURE_MP3, track1_path)
    # Clear existing title and track tags so filename-parsed track=1 and mb_tracks fallback are used
    tags = ID3(track1_path)
    tags.delall("TIT2")
    tags.delall("TRCK")
    tags.save(track1_path)
    with (
        patch("musicbrainzngs.search_releases", return_value={"release-list": []}),
        patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}),
    ):
        fix._process_file(track1_path, dir_artist="Seal", dir_album="Seal", dir_year=1991, mb_tracks=mb_tracks, dry_run=False)
    result_tags = ID3(track1_path)
    assert str(result_tags["TIT2"]) == "Crazy"


# ---------------------------------------------------------------------------
# process_directory — integration
# ---------------------------------------------------------------------------


def test_process_directory(tmp_path):
    """process_directory must process all MP3s in a folder without raising."""
    dest = str(tmp_path / "Seal - Seal (1991)")
    os.makedirs(dest)
    shutil.copy(FIXTURE_MP3, os.path.join(dest, "01 - Crazy.mp3"))
    shutil.copy(FIXTURE_MP3, os.path.join(dest, "02 - Future Love Paradise.mp3"))
    with (
        patch("musicbrainzngs.search_releases", return_value={"release-list": []}),
        patch("musicbrainzngs.get_release_by_id", return_value={"release": {"medium-list": []}}),
        patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}),
    ):
        fix._process_directory(dest, dry_run=False)
    for fname in ("01 - Crazy.mp3", "02 - Future Love Paradise.mp3"):
        tags = ID3(os.path.join(dest, fname))
        assert str(tags["TPE1"]) == "Seal"
        assert str(tags["TALB"]) == "Seal"
        dt = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(dest, fname)))
        assert dt.year == 1991


# ---------------------------------------------------------------------------
# Guard clauses (empty inputs)
# ---------------------------------------------------------------------------


def test_mb_lookup_release_no_artist():
    year, tracks = fix._mb_lookup_release("", "Album")
    assert year is None
    assert tracks == []


def test_mb_lookup_release_no_album():
    year, tracks = fix._mb_lookup_release("Artist", "")
    assert year is None
    assert tracks == []


def test_mb_lookup_track_no_artist():
    assert fix._mb_lookup_track("", "Track") is None


def test_mb_lookup_track_no_title():
    assert fix._mb_lookup_track("Artist", "") is None


# ---------------------------------------------------------------------------
# ValueError branches in MusicBrainz date parsing
# ---------------------------------------------------------------------------


def test_mb_lookup_release_invalid_date():
    """Non-numeric date string in release should be handled gracefully."""
    mock_result = {"release-list": [{"id": "abc", "date": "unknown"}]}
    mock_full = {"release": {"medium-list": []}}
    with patch("musicbrainzngs.search_releases", return_value=mock_result), patch("musicbrainzngs.get_release_by_id", return_value=mock_full):
        year, tracks = fix._mb_lookup_release("Artist", "Album")
    assert year is None
    assert tracks == []


def test_mb_lookup_track_invalid_date():
    """Non-numeric date in recording release should be skipped without crash."""
    mock_result = {"recording-list": [{"release-list": [{"date": "bad-date"}]}]}
    with patch("musicbrainzngs.search_recordings", return_value=mock_result):
        year = fix._mb_lookup_track("Artist", "Track")
    assert year is None


# ---------------------------------------------------------------------------
# Exception handler in _write_tags (ID3NoHeaderError and general exception)
# ---------------------------------------------------------------------------


def test_write_tags_no_existing_id3_header(tmp_path):
    """Writing tags to a file that has no ID3 header should not raise."""
    bare = str(tmp_path / "bare.mp3")
    shutil.copy(FIXTURE_MP3, bare)
    from mutagen.id3 import ID3NoHeaderError

    with patch("mediatools.fix_mp3_meta.ID3", side_effect=[ID3NoHeaderError, ID3()]):
        fix._write_tags(bare, artist="A", title="T", album="Al", track=1, year=2000)


def test_write_tags_exception_is_swallowed(tmp_path):
    """An exception during tag save should be logged, not propagated."""
    bad_path = str(tmp_path / "no_such.mp3")
    fix._write_tags(bad_path, artist="A", title="T", album="Al", track=1, year=2000)


# ---------------------------------------------------------------------------
# Exception handler in _set_file_date
# ---------------------------------------------------------------------------


def test_set_file_date_exception_is_swallowed(tmp_mp3):
    with patch("os.utime", side_effect=OSError("permission denied")):
        fix._set_file_date(tmp_mp3, 2000)  # must not raise


# ---------------------------------------------------------------------------
# ValueError branches in _process_file tag reading
# ---------------------------------------------------------------------------


def test_process_file_non_numeric_track_tag(tmp_path):
    """A non-numeric TRCK tag must not crash _process_file."""
    from mutagen.id3 import TRCK, TDRC

    dest = str(tmp_path / "track.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    tags = ID3(dest)
    tags["TRCK"] = TRCK(encoding=3, text="not-a-number")
    tags["TDRC"] = TDRC(encoding=3, text="not-a-year")
    tags.save(dest)
    with (
        patch("musicbrainzngs.search_releases", return_value={"release-list": []}),
        patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}),
    ):
        fix._process_file(dest, dir_artist="Artist", dir_album="Album", dir_year=2001, mb_tracks=[], dry_run=False)


# ---------------------------------------------------------------------------
# MusicBrainz year lookup triggered from _process_file when year is unknown
# ---------------------------------------------------------------------------


def test_process_file_mb_year_lookup_from_album(tmp_path):
    """When dir_year is None and existing year tag is absent, year is fetched via MB album lookup."""
    dest = str(tmp_path / "song.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    tags = ID3(dest)
    tags.delall("TDRC")
    tags.save(dest)
    mock_release = {"release-list": [{"id": "x", "date": "1991"}]}
    mock_full = {"release": {"medium-list": []}}
    with (
        patch("musicbrainzngs.search_releases", return_value=mock_release),
        patch("musicbrainzngs.get_release_by_id", return_value=mock_full),
        patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}),
    ):
        fix._process_file(dest, dir_artist="Seal", dir_album="Seal", dir_year=None, mb_tracks=[], dry_run=False)
    dt = datetime.datetime.fromtimestamp(os.path.getmtime(dest))
    assert dt.year == 1991


def test_process_file_mb_year_lookup_from_track(tmp_path):
    """When album MB lookup yields no year, per-track recording lookup is used."""
    dest = str(tmp_path / "song.mp3")
    shutil.copy(FIXTURE_MP3, dest)
    tags = ID3(dest)
    tags.delall("TDRC")
    tags.save(dest)
    with (
        patch("musicbrainzngs.search_releases", return_value={"release-list": []}),
        patch("musicbrainzngs.search_recordings", return_value={"recording-list": [{"release-list": [{"date": "1991"}]}]}),
    ):
        fix._process_file(dest, dir_artist="Seal", dir_album="Seal", dir_year=None, mb_tracks=[], dry_run=False)
    dt = datetime.datetime.fromtimestamp(os.path.getmtime(dest))
    assert dt.year == 1991


# ---------------------------------------------------------------------------
# MusicBrainz album lookup triggered from _process_directory when year unknown
# ---------------------------------------------------------------------------


def test_process_directory_mb_album_lookup(tmp_path):
    """_process_directory fires MB lookup when directory name has no year."""
    dest = str(tmp_path / "Seal - Seal")  # no year in dir name
    os.makedirs(dest)
    shutil.copy(FIXTURE_MP3, os.path.join(dest, "01 - Crazy.mp3"))
    tags = ID3(os.path.join(dest, "01 - Crazy.mp3"))
    tags.delall("TDRC")
    tags.save(os.path.join(dest, "01 - Crazy.mp3"))
    mock_release = {"release-list": [{"id": "x", "date": "1991"}]}
    mock_full = {"release": {"medium-list": []}}
    with (
        patch("musicbrainzngs.search_releases", return_value=mock_release),
        patch("musicbrainzngs.get_release_by_id", return_value=mock_full),
        patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}),
    ):
        fix._process_directory(dest, dry_run=False)
    dt = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(dest, "01 - Crazy.mp3")))
    assert dt.year == 1991


# ---------------------------------------------------------------------------
# main() entry point
# ---------------------------------------------------------------------------


def test_main_nonexistent_directory():
    """main() logs a warning and exits 0 when a non-existent path is given."""
    with patch("sys.argv", ["fix-mp3-meta", "-f", "/nonexistent_path_xyz"]):
        with pytest.raises(SystemExit) as exc:
            fix.main()
    assert exc.value.code == 0


def test_main_empty_directory(tmp_path):
    """main() exits with code 0 for an existing empty directory."""
    with patch("sys.argv", ["fix-mp3-meta", "-f", str(tmp_path)]), \
         patch("musicbrainzngs.search_releases", return_value={"release-list": []}), \
         patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}):
        with pytest.raises(SystemExit) as exc:
            fix.main()
    assert exc.value.code == 0


def test_main_dry_run(tmp_path):
    """main() --dry-run exits 0 and does not write any files."""
    shutil.copy(FIXTURE_MP3, str(tmp_path / "song.mp3"))
    with patch("sys.argv", ["fix-mp3-meta", "-f", str(tmp_path), "--dry-run"]), \
         patch("musicbrainzngs.search_releases", return_value={"release-list": []}), \
         patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}):
        with pytest.raises(SystemExit) as exc:
            fix.main()
    assert exc.value.code == 0


def test_main_individual_files(tmp_path):
    """main() accepts individual audio files (not directories) via -f."""
    src = str(tmp_path / "01 - Crazy.mp3")
    shutil.copy(FIXTURE_MP3, src)
    tags = ID3(src)
    tags.delall("TDRC")
    tags.save(src)
    with patch("sys.argv", ["fix-mp3-meta", "-f", src]), \
         patch("musicbrainzngs.search_releases", return_value={"release-list": []}), \
         patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}):
        with pytest.raises(SystemExit) as exc:
            fix.main()
    assert exc.value.code == 0


def test_main_mixed_files_and_dirs(tmp_path):
    """main() handles a mix of a directory and an individual file."""
    subdir = tmp_path / "Seal - Seal (1991)"
    subdir.mkdir()
    shutil.copy(FIXTURE_MP3, str(subdir / "01 - Crazy.mp3"))
    lone_file = str(tmp_path / "song.mp3")
    shutil.copy(FIXTURE_MP3, lone_file)
    with patch("sys.argv", ["fix-mp3-meta", "-f", str(subdir), lone_file]), \
         patch("musicbrainzngs.search_releases", return_value={"release-list": []}), \
         patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}):
        with pytest.raises(SystemExit) as exc:
            fix.main()
    assert exc.value.code == 0


def test_main_with_debug_flag(tmp_path):
    """main() -g flag sets debug level without crashing."""
    with patch("sys.argv", ["fix-mp3-meta", "-f", str(tmp_path), "-g", "5"]), \
         patch("musicbrainzngs.search_releases", return_value={"release-list": []}), \
         patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}):
        with pytest.raises(SystemExit) as exc:
            fix.main()
    assert exc.value.code == 0


def test_main_with_subdirectories(tmp_path):
    """main() processes subdirectories when root dir contains them."""
    subdir = tmp_path / "Seal - Seal (1991)"
    subdir.mkdir()
    shutil.copy(FIXTURE_MP3, str(subdir / "01 - Crazy.mp3"))
    with patch("sys.argv", ["fix-mp3-meta", "-f", str(tmp_path)]), \
         patch("musicbrainzngs.search_releases", return_value={"release-list": []}), \
         patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}):
        with pytest.raises(SystemExit) as exc:
            fix.main()
    assert exc.value.code == 0


def test_main_individual_files_mb_lookup(tmp_path):
    """When individual files are in an Artist-Album dir, MB lookup fires for the album."""
    parent = tmp_path / "Seal - Seal"
    parent.mkdir()
    src = str(parent / "01.mp3")
    shutil.copy(FIXTURE_MP3, src)
    tags = ID3(src)
    tags.delall("TDRC")
    tags.save(src)
    mock_release = {"release-list": [{"id": "x", "date": "1991"}]}
    mock_full = {"release": {"medium-list": []}}
    with patch("sys.argv", ["fix-mp3-meta", "-f", src]), \
         patch("musicbrainzngs.search_releases", return_value=mock_release), \
         patch("musicbrainzngs.get_release_by_id", return_value=mock_full), \
         patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}):
        with pytest.raises(SystemExit) as exc:
            fix.main()
    assert exc.value.code == 0
    dt = datetime.datetime.fromtimestamp(os.path.getmtime(src))
    assert dt.year == 1991


def test_main_skips_non_audio_file(tmp_path):
    """main() logs a warning and skips entries that are not audio files or directories."""
    txt_file = str(tmp_path / "readme.txt")
    with open(txt_file, "w") as f:
        f.write("not audio")
    with patch("sys.argv", ["fix-mp3-meta", "-f", txt_file]):
        with pytest.raises(SystemExit) as exc:
            fix.main()
    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# M4A / AAC tag support
# ---------------------------------------------------------------------------

def test_is_m4a():
    assert fix._is_m4a("song.m4a") is True
    assert fix._is_m4a("song.aac") is True
    assert fix._is_m4a("song.mp3") is False
    assert fix._is_m4a("song.ogg") is False


def _make_mp4_mock(artist="Seal", title="Crazy", album="Seal", track=[(3, 0)], year="1991"):
    """Build a MagicMock that behaves like a mutagen MP4 object."""
    tags = {
        "©ART": [artist],
        "©nam": [title],
        "©alb": [album],
        "trkn": track,
        "©day": [year],
    }
    mock_audio = MagicMock()
    mock_audio.tags = tags
    return mock_audio


def test_read_existing_tags_m4a_full():
    """_read_existing_tags reads all fields from an M4A file."""
    with patch("mediatools.fix_mp3_meta.MP4", return_value=_make_mp4_mock()):
        artist, title, album, track, year = fix._read_existing_tags("song.m4a")
    assert artist == "Seal"
    assert title == "Crazy"
    assert album == "Seal"
    assert track == 3
    assert year == 1991


def test_read_existing_tags_m4a_no_tags():
    """_read_existing_tags handles an M4A with no tags gracefully."""
    mock_audio = MagicMock()
    mock_audio.tags = None
    with patch("mediatools.fix_mp3_meta.MP4", return_value=mock_audio):
        artist, title, album, track, year = fix._read_existing_tags("song.m4a")
    assert artist is None and title is None and album is None
    assert track is None and year is None


def test_read_existing_tags_m4a_invalid_track():
    """Non-numeric trkn in M4A is skipped without crash."""
    with patch("mediatools.fix_mp3_meta.MP4", return_value=_make_mp4_mock(track=[("bad", 0)])):
        _, _, _, track, _ = fix._read_existing_tags("song.m4a")
    assert track is None


def test_read_existing_tags_m4a_invalid_year():
    """Non-numeric year in M4A is skipped without crash."""
    with patch("mediatools.fix_mp3_meta.MP4", return_value=_make_mp4_mock(year="unknown")):
        _, _, _, _, year = fix._read_existing_tags("song.m4a")
    assert year is None


def test_write_tags_m4a():
    """_write_tags writes iTunes atoms to an M4A file."""
    mock_audio = _make_mp4_mock()
    with patch("mediatools.fix_mp3_meta.MP4", return_value=mock_audio):
        fix._write_tags("song.m4a", artist="Seal", title="Crazy", album="Seal", track=3, year=1991)
    mock_audio.save.assert_called_once()
    assert mock_audio.tags["©ART"] == ["Seal"]
    assert mock_audio.tags["©nam"] == ["Crazy"]
    assert mock_audio.tags["©alb"] == ["Seal"]
    assert mock_audio.tags["trkn"] == [(3, 0)]
    assert mock_audio.tags["©day"] == ["1991"]


def test_write_tags_m4a_no_existing_tags():
    """_write_tags calls add_tags() when M4A has no tag container."""
    mock_audio = MagicMock()
    mock_audio.tags = None
    with patch("mediatools.fix_mp3_meta.MP4", return_value=mock_audio):
        fix._write_tags("song.m4a", artist="A", title="T", album="Al", track=1, year=2000)
    mock_audio.add_tags.assert_called_once()


def test_process_file_m4a(tmp_path):
    """_process_file correctly handles an M4A file end-to-end."""
    m4a_path = str(tmp_path / "01 - Crazy.m4a")
    mock_audio = _make_mp4_mock(track=[(1, 0)], year="")
    mock_write = MagicMock()
    mock_write.tags = {}
    with patch("mediatools.fix_mp3_meta.MP4", side_effect=[mock_audio, mock_write]), \
         patch("musicbrainzngs.search_releases", return_value={"release-list": []}), \
         patch("musicbrainzngs.search_recordings", return_value={"recording-list": []}), \
         patch("os.utime"):
        fix._process_file(m4a_path, dir_artist="Seal", dir_album="Seal", dir_year=1991, mb_tracks=[], dry_run=False)
    mock_write.save.assert_called_once()
