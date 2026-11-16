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
from unittest import mock

import pytest

import mediatools.exceptions as ex
import mediatools.utilities as util
import mediatools.videofile as video
import mediatools.volume as vol_mod
import utilities.file as fil


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
        mock.patch.object(video, "volume") as fake_volume,
    ):
        vol_mod._normalize_volume({util.INPUT_FILES: [str(f1), str(f2)], "threshold": 2.0, util.OUTPUT_FILE: str(out_csv)})
        fake_volume.assert_not_called()

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

    def fake_volume(filename: str, vol: str, output: str | None = None) -> str:
        """Simulates video.volume(): writes a new file with a postfix, as the real encode would"""
        adjusted = util.add_postfix(filename, "volume", fil.extension(filename))
        with open(adjusted, "w", encoding="utf-8") as fh:
            fh.write(f"adjusted:{vol}")
        return adjusted

    out_csv = tmp_path / "report.csv"
    with mock.patch.object(video, "get_mean_volume", side_effect=lambda f: means[f]), mock.patch.object(video, "volume", side_effect=fake_volume):
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
