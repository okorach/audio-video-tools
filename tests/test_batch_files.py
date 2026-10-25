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

"""Tests of the batch files: they don't wait at the end, and the converted ones let the tools loop on the input files (-i %*)"""

import re
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
BATCH_FILES = sorted(ROOT.glob("batch-files*/*.bat"))
TOOLS_COMMANDS = re.compile(r"\b(videotool|audiotool|imagetool|pdftool)\b")
PAUSE = re.compile(r"^\s*((::|rem)\s*)?pause\s*$", re.IGNORECASE)

# Batch files that don't loop on the files to call a tool: the tool processes all the files at once
CONVERTED = (
    "batch-files/crop",
    "batch-files/Encode AVI",
    "batch-files/encode with choices",
    "batch-files/stabilize",
    "batch-files/volume",
    "batch-files/_Pinnacle 1080p ",
    "batch-files-images/image-panorama",
    "batch-files-images/image-zoom",
    "batch-files-audio/aac",
    "batch-files-audio/mp3",
)


def lines(path: Path) -> list[str]:
    """Returns the lines of a batch file"""
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def commands(path: Path) -> list[str]:
    """The lines of a batch file that are not comments"""
    return [line.strip() for line in lines(path) if line.strip() and not line.strip().lower().startswith(("::", "rem "))]


def batch_id(path: Path) -> str:
    """Returns the id of the test of a batch file: its directory and its name"""
    return f"{path.parent.name}/{path.name}"


def test_batch_files_are_found() -> None:
    """Batch files are found"""
    assert len(BATCH_FILES) > 40


@pytest.mark.parametrize("batch_file", BATCH_FILES, ids=batch_id)
def test_batch_files_dont_pause_at_the_end(batch_file: Path) -> None:
    """Batch files dont pause at the end"""
    non_empty = [line for line in lines(batch_file) if line.strip()]
    assert non_empty, f"{batch_file.name} is empty"
    assert not PAUSE.match(non_empty[-1]), f"{batch_file.name} ends with a pause"


@pytest.mark.parametrize("name", CONVERTED)
def test_converted_batch_files_pass_all_the_files(name: str) -> None:
    """Converted batch files pass all the files"""
    batch_file = ROOT / f"{name}.bat"
    tool_commands = [line for line in commands(batch_file) if TOOLS_COMMANDS.search(line)]
    assert len(tool_commands) == 1
    assert " -i %* " in f"{tool_commands[0]} "
    assert not any(re.match(r"for\s+%%\w\s+in\s", line, re.IGNORECASE) for line in commands(batch_file))
    assert "%%~F" not in "".join(tool_commands)


def test_removed_and_renamed_batch_files() -> None:
    """Removed and renamed batch files"""
    names = {p.name for p in BATCH_FILES}
    assert "crop ffmpeg.bat" not in names
    assert "flip-h.bat" not in names
    assert "mirror.bat" not in names
    assert "video-stabilize.bat" not in names
    assert "img-zoom.bat" not in names
    assert not {"flex-encode.bat", "720p x265 25fps.bat"} & names
    assert not {"_Pinnacle 1080p CPU.bat", "_Pinnacle 1080p GPU.bat"} & names
    assert "_Pinnacle 1080p .bat" in names
    assert not {"aac 128.bat", "mp3 128.bat", "mp3 192.bat"} & names
    assert {"flip.bat", "stabilize.bat", "crop.bat", "image-zoom.bat", "image-panorama.bat", "aac.bat", "mp3.bat"} <= names


@pytest.mark.parametrize("name,profile", [("aac", "aac128"), ("mp3", "mp3_128k")])
def test_audio_batch_files_ask_for_the_bitrate(name: str, profile: str) -> None:
    """The audio bitrate is asked (128 by default, with or without the k suffix) and passed to the tool"""
    batch_file = ROOT / "batch-files-audio" / f"{name}.bat"
    content = [line.strip() for line in lines(batch_file)]
    assert "set bitrate=128" in content
    assert any(line.startswith("set /p bitrate=") for line in content)
    assert "set bitrate=!bitrate:k=!" in content
    assert f"audiotool profile-encode -i %* -p {profile} --abitrate !bitrate!k" in content


def test_pinnacle_1080p_asks_for_the_hardware_acceleration_and_the_quality():
    content = [line.strip() for line in lines(ROOT / "batch-files" / "_Pinnacle 1080p .bat")]
    assert "set hwaccel=auto" in content
    assert "set quality=high" in content
    assert any("--hw_accel !hwaccel!" in line and "--quality !quality!" in line for line in content)


@pytest.mark.parametrize("batch_file", BATCH_FILES, ids=batch_id)
def test_delayed_expansion_is_enabled_when_used(batch_file):
    """!variable! is only expanded after setlocal enabledelayedexpansion (and not when this line is a comment)"""
    if any(re.search(r"![A-Za-z_]\w*!", line) for line in commands(batch_file)):
        assert any(re.match(r"setlocal\s+enabledelayedexpansion", line, re.IGNORECASE) for line in commands(batch_file)), batch_file.name


def test_custom_encode_asks_the_resolution_and_not_the_width():
    content = [line.strip() for line in lines(ROOT / "batch-files" / "_Custom Encode.bat")]
    assert "set resolution=1920x1080" in content
    assert any(line.startswith('set /p "resolution=') for line in content)
    encode = next(line for line in content if line.startswith("videotool encode"))
    assert '--resolution "%resolution%"' in encode
    assert "--width" not in encode
    assert not any("width" in line.lower() for line in content if not line.startswith("::"))
