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

"""Tests of the string parsing functions that don't use regular expressions with a super-linear runtime:
they give the same results as the regular expressions they replace"""

import re
import time
import pytest
from mediatools import metacopy
import mediatools.utilities as util

# The regular expressions that the functions replace
OLD_OUTPUT_RE = re.compile(r'(?:"([^"]+)"|(\S+))\s*$')
OLD_ETA_RE = re.compile(r"size=.* time=(\d+:\d+:\d+\.\d+)\s+bitrate=.*speed=\s*([\d\.]+)x")


@pytest.mark.parametrize(
    "params",
    [
        '-i "in put.mp4" -vf scale=1:1 "out put.mp4"',
        "-i in.mp4 out.mp4",
        "-i in.mp4 out.mp4  ",
        '-i "in.mp4" "out.mp4"   ',
        '-i in.mp4 "out.mp4',
        '-i in.mp4 out.mp4"',
        '-i in.mp4 ""',
        '-i in.mp4 "',
        "",
        "   ",
        "single",
        '"quoted only"',
        '-i "a" -map "[v]" "o.mp4"',
    ],
)
def test_find_output_file_gives_the_same_results_as_the_regular_expression(params):
    m = OLD_OUTPUT_RE.search(params.strip())
    expected = (m.group(1) or m.group(2)) if m else None
    assert metacopy.find_output_file(params) == expected


@pytest.mark.parametrize(
    "line,expected",
    [
        ("frame=30608 fps=197 q=25.0 size=  330kB time=00:00:10.00 bitrate=2261.3kbits/s speed=10x", ("00:00:10.00", "10")),
        ("frame=  45 fps=9.4 q=28.0 size=    3072KiB time=00:00:01.72 bitrate=14631.5kbits/s speed=0.358x", ("00:00:01.72", "0.358")),
        ("frame=  10 size=N/A time=00:00:00.40 bitrate=N/A speed= 8.8x", ("00:00:00.40", "8.8")),
        ("frame=30608 fps=197 q=25.0 size=  7920kB tim=00:00:10.000 bitrate=2261.3kbits/s speed=10x", None),
        ("frame=30608 fps=197 q=25.0 size=  7920kB time=00:00:10.000 bitrate=2261.3kbits/s sped=10x", None),
        ("what the heck", None),
    ],
)
def test_progress_line_gives_the_same_results_as_the_regular_expression(line, expected):
    m = OLD_ETA_RE.search(line)
    assert (m.groups() if m else None) is None or expected is not None
    time_match = util.FFMPEG_TIME_RE.search(line) if "size=" in line else None
    speed_match = util.FFMPEG_SPEED_RE.search(line, time_match.end()) if time_match else None
    found = (time_match.group(1), speed_match.group(1)) if time_match and speed_match else None
    assert found == expected


def test_progress_line_is_parsed_fast_on_pathological_lines():
    line = "size=" + " time=" * 20000 + "x"
    start = time.perf_counter()
    assert util.__compute_eta__(line, 10) == ""
    assert time.perf_counter() - start < 1


@pytest.mark.parametrize("value,expected", [("50%", 0.5), ("-10%", -0.1), ("12.5%", 0.125), ("3", 3.0), ("2.5", 2.5)])
def test_percent_or_absolute(value, expected):
    assert util.percent_or_absolute(value) == pytest.approx(expected)


@pytest.mark.parametrize("value", ["1x5%", "a%", "%"])
def test_percent_or_absolute_rejects_malformed_percentages(value):
    with pytest.raises(ValueError, match="could not convert"):
        util.percent_or_absolute(value)


def test_output_file_name_replaces_the_colons_of_the_postfix():
    assert util.automatic_output_file_name(None, "dir/video.mp4", "1:2", "mp4").endswith("video.1-2.mp4")
    assert util.automatic_output_file_name("given.mp4", "video.mp4", "1:2") == "given.mp4"
