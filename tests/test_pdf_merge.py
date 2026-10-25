#
# media-tools
# Copyright (C) 2019-2025 Olivier Korach
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

"""Tests of the pdf-merge tool"""

import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from mediatools import tools
from mediatools import pdf_merge, pdf_split

HAS_GS = pdf_split.find_ghostscript() is not None
NB_PAGES_TOTAL = 6


def _make_pdf(path: Path, nb_pages: int) -> None:
    """Creates a PDF file of a number of pages with Ghostscript"""
    ps_code = f"/Helvetica findfont 20 scalefont setfont 1 1 {nb_pages} {{pop 50 50 moveto (x) show showpage}} for"
    cmd = [pdf_split.find_ghostscript(), "-q", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", f"-sOutputFile={path}", "-c", ps_code]
    subprocess.run(cmd, check=True)


def _touch(path: Path) -> str:
    """Creates a file with a content and returns its path"""
    path.write_bytes(b"x")
    return str(path)


def test_default_output() -> None:
    """The default output is the first input file with a _merged postfix"""
    assert pdf_merge.default_output([str(Path("a") / "foo1.pdf"), "foo2.pdf", "foo3.pdf"]) == str(Path("a") / "foo1_merged.pdf")
    assert pdf_merge.default_output(["my.doc.pdf"]) == "my.doc_merged.pdf"


def test_no_input() -> None:
    """Merging nothing is an error"""
    with pytest.raises(ValueError, match="At least 1 input"):
        pdf_merge.merge([])


def test_output_is_input(tmp_path: Path) -> None:
    """An input file can't also be the output"""
    src = _touch(tmp_path / "a.pdf")
    with pytest.raises(ValueError, match="also an input"):
        pdf_merge.merge([src], src)


def test_missing_input(tmp_path: Path) -> None:
    """A missing input file is reported"""
    with pytest.raises(FileNotFoundError):
        pdf_merge.merge([str(tmp_path / "nope.pdf")], str(tmp_path / "out.pdf"))


def test_no_ghostscript(tmp_path: Path) -> None:
    """A missing Ghostscript is reported"""
    src = _touch(tmp_path / "a.pdf")
    with mock.patch("mediatools.pdf_merge.find_ghostscript", return_value=None), pytest.raises(RuntimeError, match="Ghostscript not found"):
        pdf_merge.merge([src], str(tmp_path / "out.pdf"))


def test_merge_command(tmp_path: Path) -> None:
    """The Ghostscript command line contains the output and the inputs"""
    a, b = _touch(tmp_path / "a.pdf"), _touch(tmp_path / "b.pdf")
    with mock.patch("mediatools.pdf_merge.find_ghostscript", return_value="gs"), mock.patch("subprocess.run") as run:
        out = pdf_merge.merge([a, b])
    assert out == str(tmp_path / "a_merged.pdf")
    cmd = run.call_args[0][0]
    assert cmd[0] == "gs"
    assert f"-sOutputFile={out}" in cmd
    assert cmd[-2:] == [a, b]


def test_merge_sorts_inputs(tmp_path: Path) -> None:
    """Inputs are merged in lexicographic order"""
    files = [_touch(tmp_path / n) for n in ("c.pdf", "a.pdf", "10.pdf", "b.pdf", "2.pdf")]
    with mock.patch("mediatools.pdf_merge.find_ghostscript", return_value="gs"), mock.patch("subprocess.run") as run:
        pdf_merge.merge(files, str(tmp_path / "out.pdf"))
    merged_order = [Path(f).name for f in run.call_args[0][0][-5:]]
    assert merged_order == ["10.pdf", "2.pdf", "a.pdf", "b.pdf", "c.pdf"]


def test_main_error(tmp_path: Path) -> None:
    """main() exits with 1 and logs the error"""
    argv = ["pdftool", "merge", "-i", str(tmp_path / "nope.pdf")]
    with mock.patch.object(sys, "argv", argv), mock.patch.object(pdf_merge.log.logger, "error") as log_error, pytest.raises(SystemExit) as e:
        tools.pdftool()
    assert e.value.code == 1
    assert "not found" in str(log_error.call_args[0][1])


def test_main(tmp_path: Path) -> None:
    """main() merges the files given with -i into the file given with -o"""
    a = _touch(tmp_path / "a.pdf")
    out = str(tmp_path / "out.pdf")
    with (
        mock.patch.object(sys, "argv", ["pdftool", "merge", "-i", a, "-o", out]),
        mock.patch("mediatools.pdf_merge.merge", return_value=out) as merge,
        mock.patch.object(pdf_merge.log.logger, "info") as log_info,
    ):
        tools.pdftool()
    merge.assert_called_once_with([a], out)
    assert out in log_info.call_args[0]


@pytest.mark.skipif(not HAS_GS, reason="Ghostscript not installed")
def test_merge(tmp_path: Path) -> None:
    """Merge with the real Ghostscript, from unsorted inputs"""
    a, b, c = tmp_path / "a.pdf", tmp_path / "b.pdf", tmp_path / "c.pdf"
    _make_pdf(a, 2)
    _make_pdf(b, 3)
    _make_pdf(c, 1)
    out = str(tmp_path / "all.pdf")
    assert pdf_merge.merge([str(c), str(a), str(b)], out) == out
    assert pdf_split.page_count(pdf_split.find_ghostscript(), out) == NB_PAGES_TOTAL
