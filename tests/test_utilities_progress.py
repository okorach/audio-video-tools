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

"""Tests of the global progress/ETA logged by the tools that process several files"""

from unittest.mock import patch
import pytest
from mediatools import log
import mediatools.utilities as util
from unittest.mock import MagicMock


def progress_messages(info: MagicMock) -> list[str]:
    """Returns the global progress messages logged by a mock of the info logs"""
    return [call.args[0] % call.args[1:] for call in info.call_args_list if call.args[0].startswith("GLOBAL progress")]


def test_global_progress_eta() -> None:
    """Global progress eta"""
    with patch.object(util.time, "time", side_effect=[1000.0, 1070.0]), patch.object(log.logger, "info") as info:
        progress = util.GlobalProgress(11)
        progress.count = 6
        progress.done()
    # 7 files in 70 s: the 4 remaining files take 40 s
    assert progress_messages(info) == ["GLOBAL progress 7/11 - 63%, ETA 00:00:40.000"]


def test_global_progress_single_file_is_silent() -> None:
    """Global progress single file is silent"""
    with patch.object(log.logger, "info") as info:
        util.GlobalProgress(1).done()
    assert not progress_messages(info)


def test_process_input_files_logs_progress() -> None:
    """Process input files logs progress"""
    with patch.object(log.logger, "info") as info, patch.object(log.logger, "error"), pytest.raises(SystemExit):
        util.process_input_files({"inputfiles": ["a", "b", "c"]}, lambda f, _: 1 / 0 if f == "b" else None)
    messages = progress_messages(info)
    assert len(messages) == 3
    assert messages[0].startswith("GLOBAL progress 1/3 - 33%")
    assert messages[2].startswith("GLOBAL progress 3/3 - 100%, ETA 00:00:00")


FFMPEG_LINE = "frame=30608 fps=197 q=25.0 size=  330kB time=00:00:06.000 bitrate=2261.3kbits/s speed=2x"


def test_eta_of_a_line_combines_file_and_global_progress() -> None:
    """Eta of a line combines file and global progress"""
    # 7th file of 11 at 60%: (6 * 100 + 60) / 1100 = 60% - 660 s after the start the 40% remaining take 440 s
    with patch.object(util.time, "time", side_effect=[1000.0, 1660.0]):
        progress = util.GlobalProgress(11)
        progress.count = 6
        eta = util.__compute_eta__(FFMPEG_LINE, 10)
    assert eta == " - File progress 60%/ETA 00:00:02.000 - Global progress 60%/ETA 00:07:20.000"
    util.GlobalProgress.current = None


def test_eta_of_a_line_without_global_progress() -> None:
    """Eta of a line without global progress"""
    util.GlobalProgress(1)
    assert util.GlobalProgress.current is None
    assert util.__compute_eta__(FFMPEG_LINE, 10) == " ETA=00:00:02.000"


def test_global_progress_is_cleared_when_done() -> None:
    """Global progress is cleared when done"""
    progress = util.GlobalProgress(2)
    assert util.GlobalProgress.current is progress
    with patch.object(log.logger, "info"):
        progress.done()
        assert util.GlobalProgress.current is progress
        progress.done()
    assert util.GlobalProgress.current is None


def test_weighted_steps() -> None:
    """Weighted steps"""
    # 4 clips of weight 1 then an assembly of weight 4: at 50% of the assembly, (4 + 2) / 8 = 75% of the work is done
    with patch.object(util.time, "time", side_effect=[1000.0, 1300.0]), patch.object(log.logger, "info"):
        progress = util.GlobalProgress(8)
        progress.count = 4
        progress.next_weight = 4
        fraction, eta = progress.eta(0.5)
    assert fraction == 0.75
    assert eta == "00:01:40.000"
