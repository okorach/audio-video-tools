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

"""Tests of audiotool/videotool volume, including the --normalize batch mode"""

# The fixtures are the arguments of the tests that use them
# pylint: disable=redefined-outer-name

import csv
import os
import shutil
from pathlib import Path
from unittest import mock

import ffmpeg
import pytest

import mediatools.exceptions as ex
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.volume as vol_mod


def completed(stdout: str = "", stderr: str = "") -> mock.Mock:
    """Returns a mock of the result of a command"""
    return mock.Mock(stdout=stdout, stderr=stderr)


def test_get_mean_volume() -> None:
    """Mean volume is parsed from ffmpeg's volumedetect output"""
    stderr = "[Parsed_volumedetect_0 ...] mean_volume: -18.3 dB\n[Parsed_volumedetect_0 ...] max_volume: -2.1 dB\n"
    with mock.patch("subprocess.run", return_value=completed(stderr=stderr)):
        assert video.get_mean_volume("clip.mp3") == -18.3


def test_get_mean_volume_not_found() -> None:
    """get_mean_volume raises when ffmpeg didn't report a mean_volume"""
    with mock.patch("subprocess.run", return_value=completed(stderr="no volumedetect output here")), pytest.raises(ex.InputError):
        video.get_mean_volume("clip.mp3")


def test_normalize_volume_skips_files_within_threshold(tmp_path: pytest.TempPathFactory) -> None:
    """Files within the threshold of the average are left untouched, and no row is added to the report"""
    f1 = tmp_path / "a.mp3"
    f2 = tmp_path / "b.mp3"
    f1.write_text("a")
    f2.write_text("b")
    means = {str(f1): -20.0, str(f2): -20.5}
    out_csv = tmp_path / "report.csv"

    with (
        mock.patch.object(video, "get_mean_volume", side_effect=lambda f: means[f]),
        mock.patch.object(vol_mod, "_encode_with_volume") as fake_encode,
    ):
        vol_mod._normalize_volume({util.INPUT_FILES: [str(f1), str(f2)], "threshold": 2.0, util.OUTPUT_FILE: str(out_csv)})
        fake_encode.assert_not_called()

    assert f1.read_text() == "a"
    assert f2.read_text() == "b"
    with open(out_csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows == [list(vol_mod.CSV_HEADER)]


def test_normalize_volume_adjusts_outliers(tmp_path: pytest.TempPathFactory) -> None:
    """Files too far from the average are adjusted in place, the original is kept as .before_volume.<ext>, and reported in the CSV"""
    f1 = tmp_path / "loud.mp3"
    f2 = tmp_path / "quiet.mp3"
    f1.write_text("original-loud")
    f2.write_text("original-quiet")
    means = {str(f1): -10.0, str(f2): -30.0}  # average = -20.0, both 10dB away

    def fake_encode(_filename: str, gain: float, output: str) -> None:
        """Simulates _encode_with_volume(): writes the adjusted file"""
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(f"adjusted:{gain:.2f}dB")

    out_csv = tmp_path / "report.csv"
    with mock.patch.object(video, "get_mean_volume", side_effect=lambda f: means[f]), mock.patch.object(vol_mod, "_encode_with_volume", fake_encode):
        vol_mod._normalize_volume({util.INPUT_FILES: [str(f1), str(f2)], "threshold": 2.0, util.OUTPUT_FILE: str(out_csv)})

    before_loud = tmp_path / "loud.before_volume.mp3"
    before_quiet = tmp_path / "quiet.before_volume.mp3"
    assert before_loud.read_text() == "original-loud"
    assert before_quiet.read_text() == "original-quiet"
    assert f1.read_text() == "adjusted:-10.00dB"
    assert f2.read_text() == "adjusted:10.00dB"

    with open(out_csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    by_path = {row["full_path"]: row for row in rows}
    assert by_path[os.path.abspath(f1)]["mean_volume_db"] == "-10.00"
    assert by_path[os.path.abspath(f1)]["target_volume_db"] == "-20.00"
    assert by_path[os.path.abspath(f1)]["applied_gain_db"] == "-10.00"
    assert by_path[os.path.abspath(f1)]["backup_file"] == os.path.abspath(before_loud)
    assert by_path[os.path.abspath(f2)]["applied_gain_db"] == "+10.00"


def test_normalize_volume_default_threshold() -> None:
    """The default threshold is used when none is given"""
    assert vol_mod.DEFAULT_THRESHOLD > 0


def test_volume_and_normalize_are_mutually_exclusive() -> None:
    """--volume and --normalize can't be used together"""
    with (
        mock.patch(
            "sys.argv",
            ["media-volume", "-i", "a.mp3", "--volume", "6dB", "--normalize"],
        ),
        pytest.raises(SystemExit),
    ):
        vol_mod.main()


def test_normalize_real_ffmpeg(short_audio: str, tmp_path: pytest.TempPathFactory) -> None:
    """End to end: a quiet copy and the original converge to a common volume, and a CSV report is written"""
    loud = os.path.join(str(tmp_path), "loud.mp3")
    quiet_source = os.path.join(str(tmp_path), "quiet.mp3")
    shutil.copyfile(short_audio, loud)
    video.volume(short_audio, "-20dB", output=quiet_source)

    loud_mean_before = video.get_mean_volume(loud)
    quiet_mean_before = video.get_mean_volume(quiet_source)
    assert quiet_mean_before < loud_mean_before - 5  # the quiet copy is indeed much quieter

    out_csv = os.path.join(str(tmp_path), "report.csv")
    vol_mod._normalize_volume({util.INPUT_FILES: [loud, quiet_source], "threshold": 1.0, util.OUTPUT_FILE: out_csv})

    loud_mean_after = video.get_mean_volume(loud)
    quiet_mean_after = video.get_mean_volume(quiet_source)
    assert abs(loud_mean_after - quiet_mean_after) < abs(loud_mean_before - quiet_mean_before)

    assert os.path.isfile(util.add_postfix(loud, "before_volume", "mp3"))
    assert os.path.isfile(util.add_postfix(quiet_source, "before_volume", "mp3"))

    with open(out_csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2


def two_files(tmp_path: Path) -> tuple[Path, Path]:
    """Creates a loud and a quiet file"""
    loud, quiet = tmp_path / "loud.mp3", tmp_path / "quiet.mp3"
    loud.write_text("original-loud")
    quiet.write_text("original-quiet")
    return loud, quiet


def fake_encoder(_filename: str, _gain: float, output: str) -> None:
    """Simulates a successful _encode_with_volume()"""
    Path(output).write_text("adjusted", encoding="utf-8")


def run_normalize(files: list[Path], out_csv: Path, encoder: object = fake_encoder) -> None:
    """Normalizes files, the loud ones measured at -10 dB and the others at -30 dB, with a simulated encoding"""
    with (
        mock.patch.object(video, "get_mean_volume", side_effect=lambda f: -10.0 if "loud" in f else -30.0),
        mock.patch.object(vol_mod, "_encode_with_volume", side_effect=encoder),
    ):
        vol_mod._normalize_volume({util.INPUT_FILES: [str(f) for f in files], "threshold": 2.0, util.OUTPUT_FILE: str(out_csv)})


def test_normalize_ignores_the_backups(tmp_path: Path) -> None:
    """The backups of a previous normalization are neither measured nor modified"""
    loud, quiet = two_files(tmp_path)
    backups = [tmp_path / "loud.before_volume.mp3", tmp_path / "loud.before_volume.2.mp3"]
    for backup in backups:
        backup.write_text("backup")
    run_normalize([loud, quiet, *backups], tmp_path / "report.csv")
    assert [b.read_text() for b in backups] == ["backup", "backup"]
    assert (tmp_path / "loud.before_volume.3.mp3").read_text() == "original-loud"
    assert not list(tmp_path.glob("*before_volume*before_volume*"))


def test_normalize_never_overwrites_a_file_named_like_the_temporary_one(tmp_path: Path) -> None:
    """A user file named <file>.volume.<ext> is left untouched"""
    loud, quiet = two_files(tmp_path)
    mine = tmp_path / "loud.volume.mp3"
    mine.write_text("mine")
    run_normalize([loud, quiet], tmp_path / "report.csv")
    assert mine.read_text() == "mine"
    assert loud.read_text() == "adjusted"


def test_normalize_carries_on_after_a_failing_file(tmp_path: Path) -> None:
    """A file that fails is left as it was, without partial output, the others are adjusted and reported, and the exit code is 1"""
    loud, quiet = two_files(tmp_path)

    def encoder(filename: str, gain: float, output: str) -> None:
        """Fails on the loud file, after writing a partial output"""
        fake_encoder(filename, gain, output)
        if "loud" in filename:
            raise OSError("boom")

    out_csv = tmp_path / "report.csv"
    with pytest.raises(SystemExit) as e:
        run_normalize([loud, quiet], out_csv, encoder)
    assert e.value.code == 1
    assert loud.read_text() == "original-loud"
    assert quiet.read_text() == "adjusted"
    assert not (tmp_path / "loud.volume.mp3").exists()
    with open(out_csv, newline="", encoding="utf-8") as fh:
        assert [row["full_path"] for row in csv.DictReader(fh)] == [os.path.abspath(quiet)]


def test_normalize_skips_a_file_that_can_not_be_measured(tmp_path: Path) -> None:
    """A file whose volume can't be measured doesn't stop the others"""
    files = [*two_files(tmp_path), tmp_path / "broken.mp3"]
    files[-1].write_text("broken")

    def measure(filename: str) -> float:
        """Fails on the broken file"""
        if "broken" in filename:
            raise ex.InputError("no audio", "volume")
        return -10.0 if "loud" in filename else -30.0

    with (
        mock.patch.object(video, "get_mean_volume", side_effect=measure),
        mock.patch.object(vol_mod, "_encode_with_volume", side_effect=fake_encoder),
        pytest.raises(SystemExit),
    ):
        vol_mod._normalize_volume({util.INPUT_FILES: [str(f) for f in files], util.OUTPUT_FILE: str(tmp_path / "report.csv")})
    assert files[0].read_text() == "adjusted"
    assert files[2].read_text() == "broken"


def test_normalize_exits_when_nothing_can_be_measured(tmp_path: Path) -> None:
    """Exit code 1 when no file can be measured"""
    with mock.patch.object(video, "get_mean_volume", side_effect=OSError("boom")), pytest.raises(SystemExit):
        vol_mod._normalize_volume({util.INPUT_FILES: [str(tmp_path / "a.mp3")], util.OUTPUT_FILE: str(tmp_path / "report.csv")})


def run_volume_main(*args: str) -> dict:
    """Runs the volume command with a simulated normalization and returns the options given to it"""
    with mock.patch("sys.argv", ["media-volume", *args]), mock.patch.object(vol_mod, "_normalize_volume") as normalize:
        vol_mod.main()
    return normalize.call_args.args[0]


def test_audio_only_and_default_report_in_the_input_directory(tmp_path: Path) -> None:
    """--audio_only leaves the videos out, and the report goes in the input directory without overwriting a previous one"""
    for name in ("a.mp3", "b.mp4"):
        (tmp_path / name).write_text("x")
    options = run_volume_main("-i", str(tmp_path), "--normalize", "--audio_only")
    assert [os.path.basename(f) for f in options[util.INPUT_FILES]] == ["a.mp3"]
    assert options[util.OUTPUT_FILE] == os.path.join(str(tmp_path), "volume-normalize.csv")
    (tmp_path / "volume-normalize.csv").write_text("previous")
    options = run_volume_main("-i", str(tmp_path / "a.mp3"), "--normalize")
    assert options[util.OUTPUT_FILE] == os.path.join(str(tmp_path), "volume-normalize.2.csv")


def test_audio_only_with_only_videos(tmp_path: Path) -> None:
    """--audio_only exits with an error when there is no audio file"""
    (tmp_path / "b.mp4").write_text("x")
    with pytest.raises(SystemExit):
        run_volume_main("-i", str(tmp_path / "b.mp4"), "--normalize", "--audio_only")


@pytest.mark.parametrize(
    ("stream", "expected"),
    [
        ({"codec_name": "mp3", "bit_rate": "320000"}, "-c:a libmp3lame -b:a 320000"),
        ({"codec_name": "aac", "bit_rate": "256000"}, "-c:a aac -b:a 256000"),
        ({"codec_name": "opus"}, "-c:a libopus -b:a 99000"),
        ({"codec_name": "flac", "sample_fmt": "s32"}, "-c:a flac -sample_fmt s32"),
        ({"codec_name": "pcm_s24le"}, "-c:a pcm_s24le"),
    ],
)
def test_audio_encoding_keeps_the_codec_and_the_bitrate(stream: dict, expected: str) -> None:
    """The audio is re-encoded in its codec, at its bitrate (or the one of the file) or sample format"""
    specs = {"streams": [{"codec_type": "audio", **stream}], "format": {"bit_rate": "99000"}}
    with mock.patch.object(vol_mod.ffmpeg, "probe", return_value=specs):
        assert vol_mod._audio_encoding_options("a.xyz") == expected


@pytest.mark.parametrize(
    "streams",
    [
        [{"codec_type": "video"}],
        [{"codec_type": "audio", "codec_name": "dts", "bit_rate": "1"}],
        [{"codec_type": "video"}, {"codec_type": "audio", "codec_name": "opus"}],
    ],
)
def test_audio_encoding_refuses_to_degrade(streams: list[dict]) -> None:
    """No audio, an unsupported codec or an unknown bitrate (in a video) raise an error"""
    specs = {"streams": streams, "format": {"bit_rate": "5000000"}}
    with mock.patch.object(vol_mod.ffmpeg, "probe", return_value=specs), pytest.raises(ex.InputError):
        vol_mod._audio_encoding_options("a.xyz")


def probe_audio(filename: str) -> dict:
    """Returns the first audio stream of a file"""
    return next(s for s in ffmpeg.probe(filename, cmd=util.get_ffprobe())["streams"] if s["codec_type"] == "audio")


@pytest.mark.parametrize(
    ("name", "options"),
    [
        ("a.mp3", "-b:a 320k"),
        ("a.flac", "-sample_fmt s32"),
        ("a.m4a", "-c:a aac -b:a 192k"),
        ("a.wav", "-c:a pcm_s24le"),
        ("a.ogg", "-c:a libvorbis -b:a 160k"),
        ("a.mp4", "-c:a aac -b:a 192k"),
    ],
)
def test_encode_with_volume_real_ffmpeg(tmp_path: Path, name: str, options: str) -> None:
    """The adjusted file keeps the codec, bitrate or sample format and tags of the source, with the volume changed"""
    source, output = str(tmp_path / name), str(tmp_path / f"out.{name}")
    video_input = "-f lavfi -i color=s=64x64:d=2 " if name.endswith("mp4") else ""
    util.run_ffmpeg(f'{video_input}-f lavfi -i sine=d=2 {options} -metadata title=Song "{source}"')
    vol_mod._encode_with_volume(source, -6.0, output)
    before, after = probe_audio(source), probe_audio(output)
    assert after["codec_name"] == before["codec_name"]
    assert after.get("sample_fmt") == before.get("sample_fmt")
    if "-b:a" in options:
        assert int(after["bit_rate"]) == pytest.approx(int(before["bit_rate"]), rel=0.15)
    assert video.get_mean_volume(output) == pytest.approx(video.get_mean_volume(source) - 6, abs=1)
    tags = ffmpeg.probe(output, cmd=util.get_ffprobe())
    assert "Song" in str(tags)


def test_flac_with_cover_art_real_ffmpeg(tmp_path: Path) -> None:
    """A FLAC file with a cover art can be measured and adjusted, and keeps its cover and its sample format"""
    audio_file, cover, source, output = (str(tmp_path / name) for name in ("audio.flac", "cover.jpg", "a.flac", "out.flac"))
    util.run_ffmpeg(f'-f lavfi -i sine=d=2 -sample_fmt s32 "{audio_file}"')
    util.run_ffmpeg(f'-f lavfi -i color=red:s=64x64 -frames:v 1 "{cover}"')
    util.run_ffmpeg(f'-i "{audio_file}" -i "{cover}" -map 0 -map 1 -c copy -disposition:v attached_pic "{source}"')
    vol_mod._encode_with_volume(source, -6.0, output)
    assert video.get_mean_volume(output) == pytest.approx(video.get_mean_volume(source) - 6, abs=1)
    streams = ffmpeg.probe(output, cmd=util.get_ffprobe())["streams"]
    assert [(s["codec_name"], s.get("sample_fmt")) for s in streams] == [("flac", "s32"), ("mjpeg", None)]


def snapshot(folder: Path) -> dict[str, tuple[bytes, int]]:
    """Returns the content and the modification time of all the files of a directory"""
    return {str(f.relative_to(folder)): (f.read_bytes(), f.stat().st_mtime_ns) for f in folder.rglob("*") if f.is_file()}


def music_folder(tmp_path: Path) -> Path:
    """Creates a directory with a loud file and a quiet one in a sub directory, and an unrelated CSV file"""
    folder = tmp_path / "music"
    (folder / "cd2").mkdir(parents=True)
    (folder / "loud.mp3").write_text("original-loud")
    (folder / "cd2" / "quiet.mp3").write_text("original-quiet")
    (folder / "volume-normalize.9.csv").write_text("not,a,report")
    return folder


def test_restore_puts_the_file_system_back_after_several_normalizations(tmp_path: Path) -> None:
    """After 2 normalizations, --restore gives the same files, contents and dates, without backups nor reports"""
    folder = music_folder(tmp_path)
    before = snapshot(folder)
    files = [folder / "loud.mp3", folder / "cd2" / "quiet.mp3"]
    run_normalize(files, folder / "volume-normalize.csv")
    run_normalize(files, folder / "volume-normalize.2.csv")
    assert (folder / "loud.before_volume.2.mp3").is_file()
    with mock.patch("sys.argv", ["media-volume", "-i", str(folder), "--restore"]):
        vol_mod.main()
    assert snapshot(folder) == before


def test_restore_of_a_single_file_keeps_the_others(tmp_path: Path) -> None:
    """Restoring one file leaves the other one adjusted, with its backup and the report listing it"""
    folder = music_folder(tmp_path)
    loud, quiet = folder / "loud.mp3", folder / "cd2" / "quiet.mp3"
    report = folder / "volume-normalize.csv"
    run_normalize([loud, quiet], report)
    vol_mod._restore_volume([str(loud)])
    assert loud.read_text() == "original-loud"
    assert quiet.read_text() == "adjusted"
    assert report.is_file()
    vol_mod._restore_volume([str(folder / "cd2" / "quiet.before_volume.mp3")], str(report))
    assert quiet.read_text() == "original-quiet"
    assert not report.exists()


def test_restore_a_missing_file_and_backups_of_backups(tmp_path: Path) -> None:
    """A modified file that was deleted is restored too, and the backup of a backup is restored before the backup itself"""
    (tmp_path / "a.before_volume.mp3").write_text("adjusted-backup")
    (tmp_path / "a.before_volume.before_volume.mp3").write_text("original")
    vol_mod._restore_volume([str(tmp_path)])
    assert [f.name for f in tmp_path.iterdir()] == ["a.mp3"]
    assert (tmp_path / "a.mp3").read_text() == "original"


def test_restore_audio_only_leaves_the_videos(tmp_path: Path) -> None:
    """--audio_only restores the audio files only"""
    for name in ("a.before_volume.mp3", "v.before_volume.mp4"):
        (tmp_path / name).write_text("original")
    vol_mod._restore_volume([str(tmp_path)], audio_only=True)
    assert sorted(f.name for f in tmp_path.iterdir()) == ["a.mp3", "v.before_volume.mp4"]


def test_restore_carries_on_after_a_failure_and_keeps_the_report(tmp_path: Path) -> None:
    """A file that can't be restored doesn't stop the others; the reports are kept and the exit code is 1"""
    folder = music_folder(tmp_path)
    report = folder / "volume-normalize.csv"
    run_normalize([folder / "loud.mp3", folder / "cd2" / "quiet.mp3"], report)
    replace = Path.replace

    def failing(source: Path, target: str) -> None:
        """Fails on the loud file"""
        if "loud" in source.name:
            raise PermissionError("read only")
        replace(source, target)

    with mock.patch.object(Path, "replace", autospec=True, side_effect=failing), pytest.raises(SystemExit) as e:
        vol_mod._restore_volume([str(folder)])
    assert e.value.code == 1
    assert (folder / "cd2" / "quiet.mp3").read_text() == "original-quiet"
    assert (folder / "loud.before_volume.mp3").is_file()
    assert report.is_file()


def test_restore_without_backup_changes_nothing(tmp_path: Path) -> None:
    """Nothing is removed when there is no backup"""
    folder = music_folder(tmp_path)
    before = snapshot(folder)
    vol_mod._restore_volume([str(folder), str(tmp_path / "missing" / "a.mp3")])
    assert snapshot(folder) == before


def test_restore_excludes_the_other_modes() -> None:
    """--restore can't be used with --normalize"""
    with mock.patch("sys.argv", ["media-volume", "-i", "a.mp3", "--restore", "--normalize"]), pytest.raises(SystemExit):
        vol_mod.main()


def test_restore_applies_the_backups_in_reverse_order(tmp_path: Path) -> None:
    """The latest backup is restored first, down to the first one; after a failure, running --restore again finishes the job"""
    for name, content in (("a.mp3", "run3"), ("a.before_volume.3.mp3", "run2"), ("a.before_volume.2.mp3", "run1")):
        (tmp_path / name).write_text(content)
    (tmp_path / "a.before_volume.mp3").write_text("original")
    replace = Path.replace
    restored: list[str] = []

    def failing_on_the_first_backup(source: Path, target: str) -> None:
        """Records the backups restored, and fails on the first one once"""
        restored.append(source.name)
        if restored.count("a.before_volume.mp3") == 1 and source.name == "a.before_volume.mp3":
            raise PermissionError("locked")
        replace(source, target)

    with mock.patch.object(Path, "replace", autospec=True, side_effect=failing_on_the_first_backup):
        with pytest.raises(SystemExit):
            vol_mod._restore_volume([str(tmp_path)])
        assert restored == ["a.before_volume.3.mp3", "a.before_volume.2.mp3", "a.before_volume.mp3"]
        assert (tmp_path / "a.mp3").read_text() == "run1"
        vol_mod._restore_volume([str(tmp_path)])
    assert [f.name for f in tmp_path.iterdir()] == ["a.mp3"]
    assert (tmp_path / "a.mp3").read_text() == "original"
