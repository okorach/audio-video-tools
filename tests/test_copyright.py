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

"""Tests that all the files of the project have the same copyright notice"""

import re
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
NOTICE = re.compile(r"Copyright \(C\) (\d{4})-(\d{4}) Olivier Korach")
FIRST_YEAR = 2019
LAST_YEAR = 2026

# The files that have no notice: the license itself, the binary files, the generated files, and the files that can't hold comments
EXCLUDED_NAMES = {"LICENSE", "poetry.lock", "audio-video-tools.code-workspace", "std.rnnn"}
EXCLUDED_EXTENSIONS = {".jpg", ".mp3", ".mp4", ".xml"}


def tracked_files() -> list[Path]:
    """Returns the files tracked by git. The test is skipped if the project is not a git repository"""
    git = shutil.which("git")
    if git is None or not (ROOT / ".git").exists():
        pytest.skip("git repository required")
    out = subprocess.run([git, "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / f for f in out.split("\0") if f and (ROOT / f).is_file()]


def files_with_notice() -> list[Path]:
    """Returns the tracked files that must have a copyright notice"""
    return [f for f in tracked_files() if f.name not in EXCLUDED_NAMES and f.suffix not in EXCLUDED_EXTENSIONS]


def read(path: Path) -> str:
    """Returns the text of a file"""
    return path.read_text(encoding="utf-8", errors="replace")


def test_all_the_files_have_a_copyright_notice() -> None:
    """All the files have a copyright notice"""
    files = files_with_notice()
    assert len(files) > 200
    missing = [str(f.relative_to(ROOT)) for f in files if not NOTICE.search(read(f))]
    assert not missing, f"Files without copyright notice: {missing}"


def test_all_the_notices_cover_the_same_years() -> None:
    """All the notices cover the same years"""
    years = {}
    for f in files_with_notice():
        for first, last in NOTICE.findall(read(f)):
            years.setdefault((first, last), []).append(str(f.relative_to(ROOT)))
    assert len(years) == 1, {k: v[:5] for k, v in years.items()}
    first, last = next(iter(years))
    assert int(first) == FIRST_YEAR
    assert int(last) >= LAST_YEAR


def test_notices_are_complete_lgpl_headers() -> None:
    """Notices are complete lgpl headers"""
    for f in files_with_notice():
        text = read(f)
        assert "GNU Lesser General Public" in text, f.name
        assert "mailto:olivier.korach AT gmail DOT com" in text, f.name
