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

"""Tests of the batch files: they don't wait at the end, and the converted ones let the tools loop on the input files (-i %*)"""

import re
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
BATCH_FILES = sorted(ROOT.glob("batch-files*/*.bat"))
TOOLS_COMMANDS = re.compile(r"\b(videotool|audiotool|imagetool|pdftool)\b")
PAUSE = re.compile(r"^\s*((::|rem)\s*)?pause\s*$", re.IGNORECASE)

# Batch files that don't loop on the files to call a tool: the tool processes all the files at once
CONVERTED = ("crop", "Encode AVI", "encode with choices", "stabilize", "volume")


def lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def commands(path: Path) -> list[str]:
    """The lines of a batch file that are not comments"""
    return [line.strip() for line in lines(path) if line.strip() and not line.strip().lower().startswith(("::", "rem "))]


def batch_id(path: Path) -> str:
    return f"{path.parent.name}/{path.name}"


def test_batch_files_are_found():
    assert len(BATCH_FILES) > 40


@pytest.mark.parametrize("batch_file", BATCH_FILES, ids=batch_id)
def test_batch_files_dont_pause_at_the_end(batch_file):
    non_empty = [line for line in lines(batch_file) if line.strip()]
    assert non_empty, f"{batch_file.name} is empty"
    assert not PAUSE.match(non_empty[-1]), f"{batch_file.name} ends with a pause"


@pytest.mark.parametrize("name", CONVERTED)
def test_converted_batch_files_pass_all_the_files(name):
    batch_file = ROOT / "batch-files" / f"{name}.bat"
    tool_commands = [line for line in commands(batch_file) if TOOLS_COMMANDS.search(line)]
    assert len(tool_commands) == 1
    assert " -i %* " in f"{tool_commands[0]} "
    assert not any(re.match(r"for\s+%%\w\s+in\s", line, re.IGNORECASE) for line in commands(batch_file))
    assert "%%~F" not in "".join(tool_commands)


def test_removed_and_renamed_batch_files():
    names = {p.name for p in BATCH_FILES}
    assert "crop ffmpeg.bat" not in names
    assert "flip-h.bat" not in names
    assert "mirror.bat" not in names
    assert "video-stabilize.bat" not in names
    assert {"flip.bat", "stabilize.bat", "crop.bat"} <= names
