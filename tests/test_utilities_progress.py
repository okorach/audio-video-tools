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


def progress_messages(info) -> list[str]:
    return [call.args[0] % call.args[1:] for call in info.call_args_list if call.args[0].startswith("GLOBAL progress")]


def test_global_progress_eta():
    with patch.object(util.time, "time", side_effect=[1000.0, 1070.0]), patch.object(log.logger, "info") as info:
        progress = util.GlobalProgress(11)
        progress.count = 6
        progress.done()
    # 7 files in 70 s: the 4 remaining files take 40 s
    assert progress_messages(info) == ["GLOBAL progress 7/11 - 63%, ETA 00:00:40.000"]


def test_global_progress_single_file_is_silent():
    with patch.object(log.logger, "info") as info:
        util.GlobalProgress(1).done()
    assert not progress_messages(info)


def test_process_input_files_logs_progress():
    with patch.object(log.logger, "info") as info, patch.object(log.logger, "error"), pytest.raises(SystemExit):
        util.process_input_files({"inputfiles": ["a", "b", "c"]}, lambda f, o: 1 / 0 if f == "b" else None)
    messages = progress_messages(info)
    assert len(messages) == 3
    assert messages[0].startswith("GLOBAL progress 1/3 - 33%")
    assert messages[2].startswith("GLOBAL progress 3/3 - 100%, ETA 00:00:00")
