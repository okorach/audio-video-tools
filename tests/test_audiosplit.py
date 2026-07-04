#!python3
#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
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
import pytest
import mediatools.utilities as util
import mediatools.audiosplit as audiosplit

AUDIO_FILE = "it" + os.sep + "seal.mp3"


def test_help():
    with pytest.raises(SystemExit) as exc_info:
        util.parse_media_args(
            util.get_common_args("audio-split", "Splits a long audio file at detected tune/song changes with fade effects"),
            args=["-h"],
        )
    assert exc_info.value.code == 0


def test_bad_option():
    with pytest.raises(SystemExit) as exc_info:
        util.parse_media_args(
            util.get_common_args("audio-split", "Splits a long audio file at detected tune/song changes with fade effects"),
            args=["--nonexistent"],
        )
    assert exc_info.value.code == 2


def test_missing_input():
    with pytest.raises(SystemExit) as exc_info:
        util.parse_media_args(
            util.get_common_args("audio-split", "Splits a long audio file at detected tune/song changes with fade effects"),
            args=[],
        )
    assert exc_info.value.code == 2


def test_detect_tune_changes():
    boundaries = audiosplit.detect_tune_changes(AUDIO_FILE, sensitivity=0.5, min_segment=5)
    assert isinstance(boundaries, list)
    for b in boundaries:
        assert isinstance(b, float)
        assert b > 0


def test_dry_run(capsys):
    parser = util.get_common_args("audio-split", "Splits a long audio file at detected tune/song changes with fade effects")
    parser.add_argument("--fade-duration", required=False, type=float, default=1.0)
    parser.add_argument("--min-segment", required=False, type=float, default=30.0)
    parser.add_argument("--sensitivity", required=False, type=float, default=0.5)
    parser.add_argument("--dry-run", required=False, default=False, action="store_true")
    kwargs = util.parse_media_args(parser, args=["-i", AUDIO_FILE, "--dry-run", "--min-segment", "5"])
    input_file = kwargs.pop("inputfiles")[0]
    boundaries = audiosplit.detect_tune_changes(input_file, sensitivity=kwargs.get("sensitivity", 0.5), min_segment=kwargs.get("min_segment", 5))
    # dry run should not produce any files - just verify boundaries are returned
    assert isinstance(boundaries, list)
